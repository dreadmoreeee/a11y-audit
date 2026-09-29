from a11y_audit.engine import analyze_focus
from a11y_audit.rules import (
    at_or_above,
    axe_violation,
    own_violation,
    sort_violations,
    summarize,
    wcag_from_tags,
    wcag_label,
)


def test_wcag_tags_map_to_criteria():
    assert wcag_from_tags(["cat.color", "wcag2aa", "wcag143"]) == ["1.4.3"]
    assert wcag_from_tags(["wcag1410", "wcag2411", "wcag412", "wcag412"]) == ["1.4.10", "2.4.11", "4.1.2"]
    assert wcag_from_tags(["best-practice", "wcag21aa", "ACT"]) == []
    assert wcag_from_tags(None) == []


def test_labels():
    assert wcag_label("1.4.3") == "1.4.3 Contrast (Minimum)"
    assert wcag_label("9.9.9") == "9.9.9"
    assert wcag_label("best-practice").startswith("Best practice")


def test_fail_on_threshold():
    assert at_or_above("critical", "serious")
    assert at_or_above("serious", "serious")
    assert not at_or_above("moderate", "serious")
    assert at_or_above("minor", "minor")
    assert not at_or_above(None, "moderate")  # unknown impact counts as minor


def test_axe_violation_conversion():
    raw = {
        "id": "color-contrast", "impact": "serious", "tags": ["wcag2aa", "wcag143"],
        "help": "Elements must meet minimum color contrast ratio thresholds",
        "helpUrl": "https://dequeuniversity.com/rules/axe/4.13/color-contrast",
        "nodes": [{"target": [".a"], "html": "<p class=a>x</p>",
                   "failureSummary": "Fix any of the following:\n  low contrast 2.1:1"}] * 3,
    }
    v = axe_violation(raw, max_nodes=2)
    assert v["wcag"] == ["1.4.3"] and v["count"] == 3 and len(v["nodes"]) == 2
    assert v["nodes"][0]["selector"] == ".a"
    assert "4.5:1" in v["fix"]
    assert v["nodes"][0]["detail"] == "low contrast 2.1:1"


def test_axe_iframe_target_and_unknown_rule():
    raw = {"id": "made-up", "impact": None, "tags": ["best-practice"], "help": "Do the thing",
           "nodes": [{"target": [["iframe", "#x"]]}]}
    v = axe_violation(raw, 5)
    assert v["impact"] == "minor" and v["fix"] == "Do the thing"
    assert v["nodes"][0]["selector"] == "iframe #x"


def test_summarize_groups_by_impact_and_wcag():
    vs = [
        own_violation("focus-trap", [{"selector": "#a"}], 10),
        own_violation("text-zoom-overflow", [{"selector": "html"}, {"selector": "p"}], 10),
        {"id": "region", "impact": "moderate", "wcag": [], "count": 4},
    ]
    s = summarize(vs)
    assert s["by_impact"]["critical"] == {"rules": 1, "nodes": 1}
    assert s["by_impact"]["serious"] == {"rules": 1, "nodes": 2}
    assert list(s["by_wcag"]) == ["1.4.4", "1.4.10", "2.1.2", "best-practice"]
    assert s["by_wcag"]["best-practice"]["rules"] == ["region"]
    ordered = sort_violations(vs)
    assert [v["id"] for v in ordered] == ["focus-trap", "text-zoom-overflow", "region"]


def _step(i, y=0, **kw):
    base = {"id": i, "body": False, "selector": "#e%d" % i, "text": "", "html": "", "x": 0, "y": y,
            "w": 50, "h": 20, "vh": 800, "zero": False, "offscreen": False, "fixed": False,
            "iframe": False, "indicator": True}
    base.update(kw)
    return base


def test_focus_natural_wrap_is_not_a_trap():
    steps = [_step(1), _step(2), _step(3), {"id": 0, "body": True}, _step(1)]
    order, vs = analyze_focus(steps, tabbable_count=3)
    assert vs == []
    assert [o["selector"] for o in order] == ["#e1", "#e2", "#e3", "(document)", "#e1"]


def test_focus_cycle_within_subset_is_a_trap():
    steps = [_step(1), _step(2), _step(3), _step(2), _step(3)]
    _, vs = analyze_focus(steps, tabbable_count=6)
    assert [v["id"] for v in vs] == ["focus-trap"]
    assert [n["selector"] for n in vs[0]["nodes"]] == ["#e2", "#e3"]
    assert vs[0]["impact"] == "critical" and vs[0]["wcag"] == ["2.1.2"]


def test_focus_stuck_and_iframe_exception():
    _, vs = analyze_focus([_step(1), _step(1), _step(1)], tabbable_count=4)
    assert vs and vs[0]["id"] == "focus-trap"
    _, vs = analyze_focus([_step(1, iframe=True)] * 4, tabbable_count=4)
    assert vs == []


def test_focus_hidden_control_with_visible_label_is_fine():
    steps = [_step(1, zero=True, indicator=False, proxy=True), _step(2, indicator=False, proxy=True)]
    _, vs = analyze_focus(steps, tabbable_count=2)
    assert vs == []


def test_focus_visibility_and_jumps():
    steps = [
        _step(1, offscreen=True),
        _step(2, y=3000, indicator=False),
        _step(3, y=100),                       # jumps far up the page
        _step(4, y=120, zero=True, indicator=False),
        _step(5, y=5000, fixed=True),
        _step(6, y=10, indicator=None),        # unknown indicator is not reported
    ]
    _, vs = analyze_focus(steps, tabbable_count=6)
    by_id = {v["id"]: v for v in vs}
    assert set(by_id) == {"focus-not-visible", "focus-offscreen", "focus-order-jump"}
    assert [n["selector"] for n in by_id["focus-offscreen"]["nodes"]] == ["#e1", "#e4"]
    assert [n["selector"] for n in by_id["focus-not-visible"]["nodes"]] == ["#e2"]
    assert [n["selector"] for n in by_id["focus-order-jump"]["nodes"]] == ["#e3"]
    assert by_id["focus-not-visible"]["wcag"] == ["2.4.7"]
    assert by_id["focus-order-jump"]["wcag"] == ["2.4.3"]
