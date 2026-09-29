"""Impact levels, WCAG criterion mapping, fix hints and grouping helpers."""

from __future__ import annotations

import re
from collections import OrderedDict

IMPACTS = ("critical", "serious", "moderate", "minor")
IMPACT_RANK = {name: rank for rank, name in enumerate(IMPACTS)}

WCAG_NAMES = {
    "1.1.1": "Non-text Content",
    "1.2.2": "Captions (Prerecorded)",
    "1.3.1": "Info and Relationships",
    "1.3.2": "Meaningful Sequence",
    "1.3.5": "Identify Input Purpose",
    "1.4.1": "Use of Color",
    "1.4.2": "Audio Control",
    "1.4.3": "Contrast (Minimum)",
    "1.4.4": "Resize Text",
    "1.4.6": "Contrast (Enhanced)",
    "1.4.10": "Reflow",
    "1.4.11": "Non-text Contrast",
    "1.4.12": "Text Spacing",
    "2.1.1": "Keyboard",
    "2.1.2": "No Keyboard Trap",
    "2.2.1": "Timing Adjustable",
    "2.2.2": "Pause, Stop, Hide",
    "2.3.3": "Animation from Interactions",
    "2.4.1": "Bypass Blocks",
    "2.4.2": "Page Titled",
    "2.4.3": "Focus Order",
    "2.4.4": "Link Purpose (In Context)",
    "2.4.7": "Focus Visible",
    "2.4.11": "Focus Not Obscured (Minimum)",
    "2.5.3": "Label in Name",
    "2.5.8": "Target Size (Minimum)",
    "3.1.1": "Language of Page",
    "3.1.2": "Language of Parts",
    "3.3.2": "Labels or Instructions",
    "4.1.1": "Parsing",
    "4.1.2": "Name, Role, Value",
}

BEST_PRACTICE = "best-practice"

_TAG_RE = re.compile(r"^wcag(\d)(\d)(\d{1,2})$")

# Short fix hints for common axe rules; anything else falls back to axe's help text.
AXE_HINTS = {
    "image-alt": "Add an alt attribute; use alt=\"\" for decorative images.",
    "color-contrast": "Raise the text/background contrast to at least 4.5:1 (3:1 for large text).",
    "link-name": "Give every link discernible text (visible text, aria-label or img alt).",
    "button-name": "Give every button an accessible name (text content or aria-label).",
    "label": "Associate a <label for> or aria-label with each form field.",
    "html-has-lang": "Add a lang attribute to <html>, e.g. <html lang=\"en\">.",
    "html-lang-valid": "Use a valid BCP 47 language code in <html lang>.",
    "document-title": "Add a non-empty <title> describing the page.",
    "heading-order": "Do not skip heading levels (h2 after h1, h3 after h2).",
    "landmark-one-main": "Wrap the primary content in a single <main> element.",
    "region": "Place all content inside landmarks (header, nav, main, footer).",
    "page-has-heading-one": "Add one <h1> that names the page.",
    "list": "Only <li>, <script> or <template> may be direct children of <ul>/<ol>.",
    "listitem": "Place <li> elements inside a <ul> or <ol>.",
    "duplicate-id": "Make id attributes unique within the page.",
    "duplicate-id-aria": "Make ids referenced by ARIA attributes unique.",
    "aria-hidden-focus": "Remove focusable elements from aria-hidden containers or make them unfocusable.",
    "frame-title": "Give each <iframe> a title attribute describing its content.",
    "meta-viewport": "Do not disable zoom: remove user-scalable=no and maximum-scale<2.",
    "tabindex": "Avoid tabindex values greater than 0; reorder the DOM instead.",
    "select-name": "Associate a label with each <select>.",
    "input-image-alt": "Add alt text to <input type=\"image\">.",
    "svg-img-alt": "Give role=\"img\" SVGs a title or aria-label.",
    "link-in-text-block": "Distinguish inline links by more than color (e.g. underline).",
    "target-size": "Make touch targets at least 24x24 CSS pixels or space them apart.",
    "empty-heading": "Remove empty headings or give them text.",
    "landmark-unique": "Give repeated landmarks unique labels (aria-label).",
    "nested-interactive": "Do not nest interactive controls inside each other.",
    "scrollable-region-focusable": "Make scrollable regions keyboard reachable (tabindex=\"0\").",
    "autocomplete-valid": "Use valid autocomplete tokens on form fields.",
    "bypass": "Provide a skip link or landmarks so keyboard users can bypass repeated blocks.",
}

# Own checks: rule id -> metadata.
OWN_RULES = {
    "focus-trap": {
        "impact": "critical",
        "wcag": ["2.1.2"],
        "help": "Keyboard focus is trapped",
        "fix": "Let Tab/Shift+Tab leave the widget; only trap focus in open modal dialogs that close with Escape.",
    },
    "focus-not-visible": {
        "impact": "serious",
        "wcag": ["2.4.7"],
        "help": "Focused element shows no visible focus indicator",
        "fix": "Do not remove outlines; add a :focus-visible style (outline or box-shadow) with 3:1 contrast.",
    },
    "focus-offscreen": {
        "impact": "serious",
        "wcag": ["2.4.7", "2.4.11"],
        "help": "Focused element is off-screen or has zero size",
        "fix": "Bring focused items into view (scroll carousels to the focused slide, show skip links on :focus) or make hidden ones inert.",
    },
    "focus-order-jump": {
        "impact": "minor",
        "wcag": ["2.4.3"],
        "help": "Tab order jumps back up the page",
        "fix": "Keep DOM order aligned with visual order; avoid positive tabindex and CSS reordering.",
    },
    "text-zoom-overflow": {
        "impact": "serious",
        "wcag": ["1.4.4", "1.4.10"],
        "help": "Page scrolls horizontally with text at 200%",
        "fix": "Use relative widths (%, rem, max-width) and allow long words to wrap (overflow-wrap:anywhere).",
    },
    "text-zoom-clipped": {
        "impact": "serious",
        "wcag": ["1.4.4"],
        "help": "Text is clipped with text at 200%",
        "fix": "Avoid fixed heights with overflow:hidden on text containers; use min-height instead.",
    },
    "text-zoom-offscreen": {
        "impact": "moderate",
        "wcag": ["1.4.10"],
        "help": "Text is pushed outside the viewport with text at 200%",
        "fix": "Remove fixed widths and overflow-x:hidden on page wrappers so content can reflow.",
    },
    "motion-animation-running": {
        "impact": "moderate",
        "wcag": ["2.3.3"],
        "help": "Animation keeps running although reduced motion is requested",
        "fix": "Wrap animations in @media (prefers-reduced-motion: no-preference) or stop them under reduce.",
    },
    "motion-transition": {
        "impact": "minor",
        "wcag": ["2.3.3"],
        "help": "Movement transition is not reduced under prefers-reduced-motion",
        "fix": "Set transition-duration to 0 (or a fade) for transform/position under prefers-reduced-motion: reduce.",
    },
    "motion-smooth-scroll": {
        "impact": "minor",
        "wcag": ["2.3.3"],
        "help": "Smooth scrolling stays on under prefers-reduced-motion",
        "fix": "Only set scroll-behavior:smooth inside @media (prefers-reduced-motion: no-preference).",
    },
}


def wcag_from_tags(tags):
    """Map axe tags such as 'wcag143' or 'wcag1410' to criteria like '1.4.3'."""
    out = []
    for tag in tags or ():
        m = _TAG_RE.match(tag)
        if m:
            crit = "%s.%s.%s" % (m.group(1), m.group(2), int(m.group(3)))
            if crit not in out:
                out.append(crit)
    return out


def wcag_label(crit):
    name = WCAG_NAMES.get(crit)
    if crit == BEST_PRACTICE:
        return "Best practice (no WCAG criterion)"
    return "%s %s" % (crit, name) if name else crit


def wcag_sort_key(crit):
    if crit == BEST_PRACTICE:
        return (99, 0, 0)
    try:
        return tuple(int(p) for p in crit.split("."))
    except ValueError:
        return (98, 0, 0)


def normalize_impact(impact):
    return impact if impact in IMPACT_RANK else "minor"


def at_or_above(impact, threshold):
    """True when impact is as severe as threshold or worse."""
    return IMPACT_RANK[normalize_impact(impact)] <= IMPACT_RANK[threshold]


def summarize(violations):
    """Counts by impact and by WCAG criterion (rules and affected nodes)."""
    by_impact = OrderedDict((i, {"rules": 0, "nodes": 0}) for i in IMPACTS)
    by_wcag = {}
    for v in violations:
        bucket = by_impact[normalize_impact(v["impact"])]
        bucket["rules"] += 1
        bucket["nodes"] += v["count"]
        for crit in v["wcag"] or [BEST_PRACTICE]:
            entry = by_wcag.setdefault(crit, {"label": wcag_label(crit), "rules": [], "nodes": 0})
            entry["rules"].append(v["id"])
            entry["nodes"] += v["count"]
    ordered = OrderedDict((k, by_wcag[k]) for k in sorted(by_wcag, key=wcag_sort_key))
    return {"by_impact": by_impact, "by_wcag": ordered}


def sort_violations(violations):
    return sorted(violations, key=lambda v: (IMPACT_RANK[normalize_impact(v["impact"])], -v["count"], v["id"]))


def axe_violation(raw, max_nodes):
    """Convert one axe violation object to the report format."""
    nodes = raw.get("nodes") or []
    items = []
    for node in nodes[:max_nodes]:
        target = node.get("target") or []
        sel = " >>> ".join(t if isinstance(t, str) else " ".join(t) for t in target)
        summary = (node.get("failureSummary") or "").strip().splitlines()
        detail = " ".join(s.strip() for s in summary[1:3]) if len(summary) > 1 else ""
        items.append({"selector": sel, "html": (node.get("html") or "")[:200], "detail": detail})
    rule_id = raw.get("id", "")
    return {
        "id": rule_id,
        "source": "axe",
        "impact": normalize_impact(raw.get("impact")),
        "wcag": wcag_from_tags(raw.get("tags")),
        "help": raw.get("help", ""),
        "fix": AXE_HINTS.get(rule_id) or raw.get("help", ""),
        "help_url": raw.get("helpUrl", ""),
        "count": len(nodes),
        "nodes": items,
    }


def own_violation(rule_id, nodes, max_nodes, impact=None):
    """Build a violation for one of the tool's own checks."""
    meta = OWN_RULES[rule_id]
    return {
        "id": rule_id,
        "source": "a11y-audit",
        "impact": impact or meta["impact"],
        "wcag": list(meta["wcag"]),
        "help": meta["help"],
        "fix": meta["fix"],
        "help_url": "https://www.w3.org/WAI/WCAG22/quickref/",
        "count": len(nodes),
        "nodes": nodes[:max_nodes],
    }
