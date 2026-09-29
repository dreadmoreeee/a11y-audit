import json
import re

from a11y_audit.engine import Options, build_report
from a11y_audit.report import to_html, to_json, to_markdown, to_text
from a11y_audit.rules import own_violation, sort_violations, summarize


def _report(fail_on="serious"):
    vs = sort_violations([
        own_violation("focus-not-visible", [{"selector": "a.<b>", "detail": "no style change"}], 10),
        {"id": "color-contrast", "source": "axe", "impact": "serious", "wcag": ["1.4.3"],
         "help": "Contrast | pipe", "fix": "Raise contrast", "help_url": "https://example.invalid/r",
         "count": 12, "nodes": [{"selector": ".low", "html": "", "detail": ""}]},
        {"id": "region", "source": "axe", "impact": "moderate", "wcag": [], "help": "Landmarks",
         "fix": "Use landmarks", "help_url": "", "count": 1, "nodes": [{"selector": "div", "detail": ""}]},
    ])
    page = {"url": "https://site.test/", "final_url": "https://site.test/", "status": 200,
            "title": "Home <script>", "error": None, "tabbable": 4,
            "focus_order": [{"index": 1, "selector": "a", "text": "Home", "flags": []},
                            {"index": 2, "selector": "(document)", "text": "", "flags": []}],
            "axe": {"version": "4.13.0", "passes": 30, "incomplete": 2},
            "violations": vs, "summary": summarize(vs), "check_errors": []}
    broken = {"url": "https://down.test/", "final_url": None, "status": None, "title": None,
              "error": "net::ERR_CONNECTION_REFUSED", "tabbable": None, "focus_order": [],
              "axe": None, "violations": [], "check_errors": []}
    return build_report([page, broken], Options(fail_on=fail_on))


def test_report_totals_and_fail_flag():
    r = _report()
    assert r["failed"] is True and r["errors"] == 1
    assert r["totals"]["by_impact"]["serious"]["rules"] == 2
    assert r["axe_version"] == "4.13.0"
    assert _report("critical")["failed"] is False
    assert _report(None)["failed"] is False


def test_json_round_trip():
    data = json.loads(to_json(_report()))
    assert data["pages"][0]["violations"][0]["impact"] == "serious"
    assert data["options"]["viewport"] == "1280x800"
    assert "user_agent" not in data["options"]


def test_markdown_groups():
    md = to_markdown(_report())
    assert "## https://site.test/" in md
    assert "### By WCAG criterion" in md
    assert "| 1.4.3 Contrast (Minimum) | color-contrast | 12 |" in md
    assert "#### Serious" in md and "#### Moderate" in md
    assert "Contrast \\| pipe" in md
    assert "... 11 more" in md
    assert "Could not audit: net::ERR_CONNECTION_REFUSED" in md
    assert "**fail-on serious: FAILED**" in md


def test_html_is_self_contained_and_escaped():
    out = to_html(_report())
    assert out.startswith("<!DOCTYPE html>")
    assert "<script" not in out.lower().replace("&lt;script&gt;", "")
    assert "Home &lt;script&gt;" in out
    assert "a.&lt;b&gt;" in out
    # no external resources: only anchors may point outside
    assert not re.search(r"<(link|img|script)[^>]+(src|href)=", out)
    assert 'lang="en"' in out
    out.encode("ascii")


def test_text_summary():
    txt = to_text(_report())
    assert "serious   color-contrast [1.4.3] x12" in txt
    assert "ERROR: net::ERR_CONNECTION_REFUSED" in txt
    assert "fail-on serious: FAILED" in txt
    assert "Keyboard sample: 1 Tab stops, 1 distinct elements, 4 tabbable on page" in txt
