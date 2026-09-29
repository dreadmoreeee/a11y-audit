"""Drive headless Chromium, run axe-core and the tool's own checks."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from . import checks_js as js
from .rules import (
    IMPACTS,
    at_or_above,
    axe_violation,
    own_violation,
    sort_violations,
    summarize,
)

DEFAULT_USER_AGENT = "a11y-audit/1.0 (+https://github.com/dreadmoreeee/a11y-audit)"
CHECKS = ("axe", "motion", "focus", "zoom")
AXE_PATH = Path(__file__).parent / "vendor" / "axe.min.js"


@dataclass
class Options:
    max_tabs: int = 30
    motion_threshold_ms: int = 250
    zoom_factor: float = 2.0
    viewport: tuple = (1280, 800)
    timeout_s: float = 30.0
    delay_s: float = 1.0
    settle_ms: int = 800
    focus_settle_ms: int = 700
    user_agent: str = DEFAULT_USER_AGENT
    skip: list = field(default_factory=list)
    best_practice: bool = True
    max_nodes: int = 10
    fail_on: str | None = None


def load_axe_source():
    return AXE_PATH.read_text(encoding="utf-8")


def analyze_focus(steps, tabbable_count, max_nodes=10):
    """Turn a list of FOCUS_STEP results into (order, violations).

    Detects focus stuck on one element, cycles within a subset of the
    tabbable elements, invisible focus, off-screen focus and upward jumps.
    """
    order = []
    violations = []
    trap = None
    visited = []  # ids since the last time focus returned to the document
    last_real = None
    stuck = 0
    for index, step in enumerate(steps, 1):
        if step.get("body"):
            if not order:
                continue
            order.append({"index": index, "selector": "(document)", "text": "", "flags": []})
            visited = []
            stuck = 0
            continue
        flags = []
        shown_elsewhere = step["indicator"] is True or step.get("proxy") is True
        if step["offscreen"]:
            flags.append("off-screen")
        elif step["zero"]:
            # visually hidden control (custom radio/checkbox) is fine if a label or sibling reacts
            if not shown_elsewhere:
                flags.append("zero-size")
        elif step["indicator"] is False and not shown_elsewhere:
            flags.append("no-visible-focus")
        prev = last_real
        if prev is not None and prev["id"] == step["id"]:
            stuck += 1
            if stuck >= 2 and not step["iframe"] and tabbable_count > 1 and trap is None:
                trap = ("stuck", [step])
        else:
            stuck = 0
            if step["id"] in visited and trap is None:
                start = visited.index(step["id"])
                cycle = visited[start:]
                if len(set(visited)) < tabbable_count:
                    members = {s["id"]: s for s in steps[:index] if not s.get("body")}
                    trap = ("cycle", [members[i] for i in cycle])
        if (prev is not None and prev["id"] != step["id"] and not step["fixed"] and not prev["fixed"]
                and "off-screen" not in flags and "zero-size" not in flags
                and step["y"] + step["h"] < prev["y"] - step["vh"]):
            flags.append("jumps-up")
        visited.append(step["id"])
        last_real = step
        order.append({"index": index, "selector": step["selector"], "text": step["text"], "flags": flags,
                      "html": step.get("html", ""), "id": step["id"]})

    def uniq(flag, detail):
        seen, nodes = set(), []
        for item in order:
            if flag in item["flags"] and item.get("id") not in seen:
                seen.add(item["id"])
                nodes.append({"selector": item["selector"], "html": item.get("html", ""),
                              "detail": "%s (Tab stop %d)" % (detail, item["index"])})
        return nodes

    if trap:
        kind, members = trap
        if kind == "stuck":
            detail = "focus stays here after repeated Tab presses"
        else:
            detail = "focus cycles among %d element(s) of %d tabbable" % (len(members), tabbable_count)
        nodes = [{"selector": m["selector"], "html": m.get("html", ""), "detail": detail} for m in members]
        violations.append(own_violation("focus-trap", nodes, max_nodes))
    for rule, flag_names, detail in (
        ("focus-not-visible", ("no-visible-focus",), "no style change on focus"),
        ("focus-offscreen", ("off-screen", "zero-size"), "not visible while focused"),
        ("focus-order-jump", ("jumps-up",), "focus moved more than one viewport up"),
    ):
        nodes = []
        for flag in flag_names:
            nodes.extend(uniq(flag, flag.replace("-", " ") if rule == "focus-offscreen" else detail))
        if nodes:
            violations.append(own_violation(rule, nodes, max_nodes))
    for item in order:
        item.pop("id", None)
        item.pop("html", None)
    return order, violations


def _run_axe(page, axe_source, opts):
    page.evaluate(axe_source + "\n;true")
    run_opts = {"resultTypes": ["violations"]}
    if not opts.best_practice:
        run_opts["runOnly"] = {"type": "tag", "values": [
            "wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]}
    res = page.evaluate(
        """async (o) => {
            const r = await axe.run(document, o);
            return {version: axe.version, violations: r.violations, incomplete: r.incomplete.length,
                    passes: r.passes.length};
        }""",
        run_opts,
    )
    violations = [axe_violation(v, opts.max_nodes) for v in res["violations"]]
    return violations, {"version": res["version"], "passes": res["passes"], "incomplete": res["incomplete"]}


def _run_motion(page, opts):
    res = page.evaluate(js.MOTION, {"thresholdMs": opts.motion_threshold_ms})
    out = []
    if res["running"]:
        out.append(own_violation("motion-animation-running", res["running"], opts.max_nodes))
    if res["transitions"]:
        out.append(own_violation("motion-transition", res["transitions"], opts.max_nodes))
    if res["smooth"]:
        out.append(own_violation("motion-smooth-scroll", res["smooth"], opts.max_nodes))
    return out


def _run_focus(page, opts):
    tabbable = page.evaluate(js.FOCUS_SNAPSHOT)
    steps = []
    since_body = []
    for _ in range(max(0, opts.max_tabs)):
        page.keyboard.press("Tab")
        page.wait_for_timeout(60)
        step = page.evaluate(js.FOCUS_STEP)
        if not step.get("body") and (step["offscreen"] or step["zero"] or step["indicator"] is False):
            # give scripted carousels and focus transitions time to settle before judging
            page.wait_for_timeout(opts.focus_settle_ms)
            step = page.evaluate(js.FOCUS_STEP)
        steps.append(step)
        if step.get("body"):
            if since_body:
                break  # reached the end of the tab order
            continue
        if len(steps) >= 3 and not step["iframe"] and steps[-2].get("id") == step["id"] == steps[-3].get("id"):
            break  # stuck; no point pressing further
        if (step["id"] in since_body and since_body[-1] != step["id"]
                and len(set(since_body)) < tabbable):
            break  # cycling within a subset
        since_body.append(step["id"])
    order, violations = analyze_focus(steps, tabbable, opts.max_nodes)
    return tabbable, order, violations


def _run_zoom(page, opts):
    page.evaluate(js.TEXT_ZOOM, {"phase": "before"})
    page.evaluate(js.TEXT_ZOOM, {"phase": "apply", "factor": opts.zoom_factor})
    page.wait_for_timeout(300)
    res = page.evaluate(js.TEXT_ZOOM, {"phase": "after"})
    out = []
    if res["overflow"]:
        out.append(own_violation("text-zoom-overflow", res["overflow"], opts.max_nodes))
    if res["clipped"]:
        out.append(own_violation("text-zoom-clipped", res["clipped"], opts.max_nodes))
    if res["offscreen"]:
        out.append(own_violation("text-zoom-offscreen", res["offscreen"], opts.max_nodes))
    return out


def audit_page(context, url, opts, axe_source):
    page_result = {
        "url": url, "final_url": None, "status": None, "title": None, "error": None,
        "tabbable": None, "focus_order": [], "axe": None, "violations": [], "check_errors": [],
    }
    page = context.new_page()
    try:
        page.emulate_media(reduced_motion="reduce")
        try:
            resp = page.goto(url, wait_until="load", timeout=int(opts.timeout_s * 1000))
        except Exception as exc:  # network error, timeout, bad URL
            page_result["error"] = str(exc).splitlines()[0]
            return page_result
        page_result["status"] = resp.status if resp else None
        page_result["final_url"] = page.url
        if resp is not None and resp.status >= 400:
            page_result["error"] = "HTTP %d" % resp.status
            return page_result
        try:
            page.wait_for_load_state("networkidle", timeout=3000)
        except Exception:
            pass
        page.wait_for_timeout(opts.settle_ms)
        page_result["title"] = page.title()
        page.evaluate(js.HELPERS)
        violations = []
        for check in CHECKS:
            if check in opts.skip:
                continue
            try:
                if check == "axe":
                    found, page_result["axe"] = _run_axe(page, axe_source, opts)
                elif check == "motion":
                    found = _run_motion(page, opts)
                elif check == "focus":
                    page_result["tabbable"], page_result["focus_order"], found = _run_focus(page, opts)
                else:
                    found = _run_zoom(page, opts)
                violations.extend(found)
            except Exception as exc:
                page_result["check_errors"].append({"check": check, "error": str(exc).splitlines()[0]})
        page_result["violations"] = sort_violations(violations)
        page_result["summary"] = summarize(page_result["violations"])
        return page_result
    finally:
        page.close()


def _guard_route(route):
    # Only read the site: let GET/HEAD through, never send data.
    if route.request.method in ("GET", "HEAD", "OPTIONS"):
        route.continue_()
    else:
        route.abort()


def audit_urls(urls, opts=None, log=None):
    """Audit each URL and return the full report dictionary."""
    from playwright.sync_api import sync_playwright

    opts = opts or Options()
    axe_source = load_axe_source()
    pages = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                viewport={"width": opts.viewport[0], "height": opts.viewport[1]},
                user_agent=opts.user_agent,
                reduced_motion="reduce",
                bypass_csp=True,
                locale="en-US",
            )
            context.route("**/*", _guard_route)
            last = None
            for url in urls:
                if last is not None:
                    wait = opts.delay_s - (time.monotonic() - last)
                    if wait > 0:
                        time.sleep(wait)
                if log:
                    log("auditing %s" % url)
                last = time.monotonic()
                pages.append(audit_page(context, url, opts, axe_source))
            context.close()
        finally:
            browser.close()
    return build_report(pages, opts)


def build_report(pages, opts):
    all_violations = [v for p in pages for v in p.get("violations", [])]
    failed = False
    if opts.fail_on:
        failed = any(at_or_above(v["impact"], opts.fail_on) for v in all_violations)
    options = asdict(opts)
    options["viewport"] = "%dx%d" % tuple(opts.viewport)
    options.pop("user_agent", None)
    axe_version = next((p["axe"]["version"] for p in pages if p.get("axe")), None)
    return {
        "tool": "a11y-audit",
        "version": __version__,
        "axe_version": axe_version,
        "generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "options": options,
        "pages": pages,
        "totals": summarize(all_violations),
        "impacts": list(IMPACTS),
        "fail_on": opts.fail_on,
        "failed": failed,
        "errors": sum(1 for p in pages if p.get("error")),
    }
