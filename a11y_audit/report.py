"""Render an audit report as text, JSON, Markdown or self-contained HTML."""

from __future__ import annotations

import html
import json

from .rules import IMPACTS


def to_json(report):
    return json.dumps(report, indent=2, ensure_ascii=True) + "\n"


def _counts(page):
    summary = page.get("summary") or {}
    by_impact = summary.get("by_impact") or {}
    return [by_impact.get(i, {}).get("nodes", 0) for i in IMPACTS]


def _rule_counts(page):
    summary = page.get("summary") or {}
    by_impact = summary.get("by_impact") or {}
    return [by_impact.get(i, {}).get("rules", 0) for i in IMPACTS]


def _wcag(v):
    return ", ".join(v["wcag"]) if v["wcag"] else "best practice"


def _header_line(report):
    o = report["options"]
    parts = ["a11y-audit %s" % report["version"]]
    if report.get("axe_version"):
        parts.append("axe-core %s" % report["axe_version"])
    parts.append("viewport %s" % o["viewport"])
    parts.append("reduced motion emulated")
    parts.append("text zoom %d%%" % round(o["zoom_factor"] * 100))
    return ", ".join(parts)


def _focus_line(page):
    stops = [f for f in page["focus_order"] if f["selector"] != "(document)"]
    distinct = len({f["selector"] for f in stops})
    return "Keyboard sample: %d Tab stops, %d distinct elements, %d tabbable on page" % (
        len(stops), distinct, page["tabbable"])


def _verdict(report):
    if report.get("fail_on"):
        return "fail-on %s: %s" % (report["fail_on"], "FAILED" if report["failed"] else "passed")
    return ""


# ---------------------------------------------------------------- text

def to_text(report, max_selectors=3):
    lines = [_header_line(report), ""]
    for page in report["pages"]:
        lines.append(page["url"])
        if page.get("error"):
            lines.append("  ERROR: %s" % page["error"])
            lines.append("")
            continue
        if page.get("final_url") and page["final_url"] != page["url"]:
            lines.append("  final URL: %s" % page["final_url"])
        rules = _rule_counts(page)
        nodes = _counts(page)
        lines.append("  " + "  ".join("%s %d (%d nodes)" % (i, r, n) for i, r, n in zip(IMPACTS, rules, nodes)))
        if page.get("tabbable") is not None:
            lines.append("  " + _focus_line(page))
        for v in page["violations"]:
            lines.append("  %-9s %s [%s] x%d  %s" % (v["impact"], v["id"], _wcag(v), v["count"], v["help"]))
            for n in v["nodes"][:max_selectors]:
                lines.append("            - %s" % n["selector"])
            if v["count"] > max_selectors:
                lines.append("            ... %d more" % (v["count"] - min(max_selectors, len(v["nodes"]))))
            lines.append("            fix: %s" % v["fix"])
        for err in page.get("check_errors", []):
            lines.append("  check %s failed: %s" % (err["check"], err["error"]))
        lines.append("")
    total = report["totals"]["by_impact"]
    lines.append("Total: " + ", ".join("%s %d" % (i, total[i]["rules"]) for i in IMPACTS)
                 + " (rules); pages %d, errors %d" % (len(report["pages"]), report["errors"]))
    verdict = _verdict(report)
    if verdict:
        lines.append(verdict)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- markdown

def _md(text):
    return str(text).replace("|", "\\|").replace("\n", " ").replace("<", "&lt;")


def to_markdown(report):
    out = ["# Accessibility audit", "", _header_line(report) + ". Generated %s." % report["generated"], ""]
    out.append("| Page | Status | " + " | ".join(i.capitalize() for i in IMPACTS) + " |")
    out.append("|---|---|" + "---:|" * len(IMPACTS))
    for page in report["pages"]:
        status = page["error"] if page.get("error") else str(page.get("status"))
        counts = _rule_counts(page)
        out.append("| %s | %s | %s |" % (_md(page["url"]), _md(status), " | ".join(str(c) for c in counts)))
    out.append("")
    out.append("Counts are rules; each rule may affect several elements.")
    verdict = _verdict(report)
    if verdict:
        out += ["", "**%s**" % verdict]
    for page in report["pages"]:
        out += ["", "## %s" % page["url"], ""]
        if page.get("error"):
            out += ["Could not audit: %s" % _md(page["error"])]
            continue
        if page.get("title"):
            out.append("Title: %s  " % _md(page["title"]))
        if page.get("axe"):
            out.append("axe: %d violations, %d passes, %d need review  " % (
                sum(1 for v in page["violations"] if v["source"] == "axe"),
                page["axe"]["passes"], page["axe"]["incomplete"]))
        if page.get("tabbable") is not None:
            out.append(_focus_line(page))
        by_wcag = page["summary"]["by_wcag"]
        if by_wcag:
            out += ["", "### By WCAG criterion", "", "| Criterion | Rules | Elements |", "|---|---|---:|"]
            for entry in by_wcag.values():
                out.append("| %s | %s | %d |" % (_md(entry["label"]), ", ".join(entry["rules"]), entry["nodes"]))
        if page["violations"]:
            out += ["", "### Violations by impact"]
            for impact in IMPACTS:
                group = [v for v in page["violations"] if v["impact"] == impact]
                if not group:
                    continue
                out += ["", "#### %s" % impact.capitalize()]
                for v in group:
                    out += ["", "- **%s** (%s, WCAG %s, %d element%s): %s" % (
                        v["id"], v["source"], _wcag(v), v["count"], "" if v["count"] == 1 else "s", _md(v["help"]))]
                    out.append("  - Fix: %s" % _md(v["fix"]))
                    for n in v["nodes"]:
                        detail = (" - %s" % _md(n["detail"])) if n.get("detail") else ""
                        out.append("  - `%s`%s" % (n["selector"].replace("`", "'"), detail))
                    if v["count"] > len(v["nodes"]):
                        out.append("  - ... %d more" % (v["count"] - len(v["nodes"])))
        else:
            out += ["", "No violations found."]
        for err in page.get("check_errors", []):
            out.append("")
            out.append("Check `%s` failed: %s" % (err["check"], _md(err["error"])))
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- html

_CSS = """
body{font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;color:#1b1b1b;background:#f6f6f4}
main{max-width:1100px;margin:0 auto;padding:24px}
h1{margin:0 0 4px}h2{margin-top:40px;border-bottom:2px solid #ddd;padding-bottom:4px;word-break:break-all}
table{border-collapse:collapse;width:100%;background:#fff;margin:12px 0}
th,td{border:1px solid #ccc;padding:6px 8px;text-align:left;vertical-align:top}
td.n{text-align:right}
.badge{display:inline-block;border-radius:4px;padding:1px 8px;font-weight:700;font-size:13px;color:#fff}
.critical{background:#8b0000}.serious{background:#b3261e}.moderate{background:#8a5300}.minor{background:#3d5a80}
details{background:#fff;border:1px solid #ccc;border-radius:6px;margin:8px 0;padding:8px 12px}
summary{cursor:pointer}
code{background:#eee;padding:1px 4px;border-radius:3px;word-break:break-all}
.muted{color:#555}.fail{color:#b3261e;font-weight:700}.pass{color:#1e6b2e;font-weight:700}
a{color:#0b57d0}
a:focus-visible,summary:focus-visible{outline:3px solid #0b57d0;outline-offset:2px}
"""


def _e(text):
    return html.escape(str(text), quote=True)


def to_html(report):
    h = ['<!DOCTYPE html>', '<html lang="en">', '<head>', '<meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1">',
         '<title>Accessibility audit</title>', '<style>%s</style>' % _CSS, '</head>', '<body>', '<main>',
         '<h1>Accessibility audit</h1>',
         '<p class="muted">%s. Generated %s.</p>' % (_e(_header_line(report)), _e(report["generated"]))]
    verdict = _verdict(report)
    if verdict:
        h.append('<p class="%s">%s</p>' % ("fail" if report["failed"] else "pass", _e(verdict)))
    h.append('<table><caption class="muted">Rules violated per page (elements in parentheses)</caption>')
    h.append('<tr><th scope="col">Page</th><th scope="col">Status</th>'
             + "".join('<th scope="col">%s</th>' % i.capitalize() for i in IMPACTS) + '</tr>')
    for idx, page in enumerate(report["pages"]):
        status = page["error"] if page.get("error") else page.get("status")
        cells = "".join('<td class="n">%d (%d)</td>' % (r, n) for r, n in zip(_rule_counts(page), _counts(page)))
        h.append('<tr><td><a href="#page-%d">%s</a></td><td>%s</td>%s</tr>' % (
            idx, _e(page["url"]), _e(status), cells))
    h.append('</table>')
    for idx, page in enumerate(report["pages"]):
        h.append('<section aria-labelledby="page-%d"><h2 id="page-%d">%s</h2>' % (idx, idx, _e(page["url"])))
        if page.get("error"):
            h.append('<p class="fail">Could not audit: %s</p></section>' % _e(page["error"]))
            continue
        meta = []
        if page.get("title"):
            meta.append("Title: %s" % _e(page["title"]))
        if page.get("axe"):
            meta.append("axe passes: %d, needs review: %d" % (page["axe"]["passes"], page["axe"]["incomplete"]))
        if page.get("tabbable") is not None:
            meta.append(_e(_focus_line(page)))
        if meta:
            h.append('<p class="muted">%s</p>' % "<br>".join(meta))
        by_wcag = page["summary"]["by_wcag"]
        if by_wcag:
            h.append('<h3>By WCAG criterion</h3><table><tr><th scope="col">Criterion</th>'
                     '<th scope="col">Rules</th><th scope="col">Elements</th></tr>')
            for entry in by_wcag.values():
                h.append('<tr><td>%s</td><td>%s</td><td class="n">%d</td></tr>' % (
                    _e(entry["label"]), _e(", ".join(entry["rules"])), entry["nodes"]))
            h.append('</table>')
        if page["violations"]:
            h.append('<h3>Violations by impact</h3>')
        else:
            h.append('<p class="pass">No violations found.</p>')
        for v in page["violations"]:
            h.append('<details><summary><span class="badge %s">%s</span> <strong>%s</strong> '
                     '<span class="muted">WCAG %s, %d element%s, %s</span> %s</summary>' % (
                         _e(v["impact"]), _e(v["impact"]), _e(v["id"]), _e(_wcag(v)), v["count"],
                         "" if v["count"] == 1 else "s", _e(v["source"]), _e(v["help"])))
            h.append('<p><strong>Fix:</strong> %s' % _e(v["fix"]))
            if v.get("help_url"):
                h.append(' <a href="%s">Reference</a>' % _e(v["help_url"]))
            h.append('</p><ul>')
            for n in v["nodes"]:
                detail = (' <span class="muted">%s</span>' % _e(n["detail"])) if n.get("detail") else ""
                h.append('<li><code>%s</code>%s</li>' % (_e(n["selector"]), detail))
            if v["count"] > len(v["nodes"]):
                h.append('<li class="muted">... %d more</li>' % (v["count"] - len(v["nodes"])))
            h.append('</ul></details>')
        if page.get("focus_order"):
            h.append('<details><summary>Keyboard focus order sample</summary><table><tr><th scope="col">#</th>'
                     '<th scope="col">Element</th><th scope="col">Text</th><th scope="col">Flags</th></tr>')
            for f in page["focus_order"]:
                h.append('<tr><td class="n">%d</td><td><code>%s</code></td><td>%s</td><td>%s</td></tr>' % (
                    f["index"], _e(f["selector"]), _e(f["text"]), _e(", ".join(f["flags"]))))
            h.append('</table></details>')
        for err in page.get("check_errors", []):
            h.append('<p class="fail">Check %s failed: %s</p>' % (_e(err["check"]), _e(err["error"])))
        h.append('</section>')
    h.append('<p class="muted">Automated checks find only part of all accessibility issues; '
             'review results manually. axe-core is licensed under MPL-2.0.</p>')
    h += ['</main>', '</body>', '</html>']
    return "\n".join(h) + "\n"


RENDERERS = {"text": to_text, "json": to_json, "markdown": to_markdown, "html": to_html}
