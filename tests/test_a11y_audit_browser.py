"""End-to-end checks in headless Chromium against local fixture pages."""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _ids(page):
    return {v["id"]: v for v in page["violations"]}


def test_accessible_page_is_clean(fixture_report):
    pages, _ = fixture_report
    good = pages["good.html"]
    assert good["error"] is None and good["check_errors"] == []
    assert good["violations"] == []
    assert good["axe"]["version"].startswith("4.")
    # includes a visually hidden radio whose label shows focus, and a link revealed 300 ms after focus
    assert good["tabbable"] == 7
    stops = [f for f in good["focus_order"] if f["selector"] != "(document)"]
    assert len(stops) == 7 and all(f["flags"] == [] for f in stops)


def test_broken_page_axe_findings(fixture_report):
    bad = _ids(fixture_report[0]["bad.html"])
    for rule in ("image-alt", "label", "button-name", "color-contrast", "html-has-lang", "document-title"):
        assert rule in bad, rule
    assert bad["image-alt"]["impact"] == "critical"
    assert bad["color-contrast"]["wcag"] == ["1.4.3"]
    assert bad["html-has-lang"]["wcag"] == ["3.1.1"]


def test_broken_page_focus_findings(fixture_report):
    bad = _ids(fixture_report[0]["bad.html"])
    assert [n["selector"] for n in bad["focus-offscreen"]["nodes"]] == ["body > a:nth-of-type(1)"]
    invisible = [n["selector"] for n in bad["focus-not-visible"]["nodes"]]
    assert "body > a:nth-of-type(2)" in invisible and "body > button:nth-of-type(1)" in invisible
    assert "body > input" not in invisible  # the input keeps the default focus ring
    assert "focus-trap" not in bad


def test_broken_page_zoom_findings(fixture_report):
    bad = _ids(fixture_report[0]["bad.html"])
    assert bad["text-zoom-overflow"]["wcag"] == ["1.4.4", "1.4.10"]
    clipped = [n["selector"] for n in bad["text-zoom-clipped"]["nodes"]]
    assert clipped == ["body > div:nth-of-type(1)"]


def test_broken_page_motion_findings(fixture_report):
    bad = _ids(fixture_report[0]["bad.html"])
    running = bad["motion-animation-running"]
    assert running["nodes"][0]["selector"] == "body > span"
    assert "infinite" in running["nodes"][0]["detail"]
    assert bad["motion-transition"]["nodes"][0]["detail"].startswith("transform 600 ms")
    assert "motion-smooth-scroll" in bad
    assert all(v["wcag"] == ["2.3.3"] for k, v in bad.items() if k.startswith("motion-"))


def test_focus_cycle_trap(fixture_report):
    trap = fixture_report[0]["trap.html"]
    v = _ids(trap)["focus-trap"]
    assert v["impact"] == "critical" and v["wcag"] == ["2.1.2"]
    assert [n["selector"] for n in v["nodes"]] == ["#b", "#c"]
    assert len(trap["focus_order"]) < 10  # stopped early


def test_focus_stuck_trap(fixture_report):
    stuck = _ids(fixture_report[0]["stuck.html"])
    assert [n["selector"] for n in stuck["focus-trap"]["nodes"]] == ["#q"]


def test_report_level_flags(fixture_report):
    _, report = fixture_report
    assert report["failed"] is True and report["errors"] == 0
    assert report["totals"]["by_impact"]["critical"]["rules"] >= 5


def _cli(*args, cwd):
    env = dict(os.environ, PYTHONUTF8="1", PYTHONPATH=str(ROOT))
    return subprocess.run([sys.executable, "-m", "a11y_audit", "-q", "--delay", "0", *args],
                          capture_output=True, text=True, cwd=cwd, env=env, timeout=240)


def test_cli_exit_codes_and_outputs(fixture_server, closed_port_url, tmp_path):
    ok = _cli(fixture_server + "good.html", "--fail-on", "minor", "--skip", "zoom", cwd=tmp_path)
    assert ok.returncode == 0, ok.stderr
    assert "critical 0 (0 nodes)" in ok.stdout

    out = tmp_path / "r"
    bad = _cli(fixture_server + "bad.html", fixture_server + "good.html", "--fail-on", "critical",
               "--skip", "focus", "--skip", "zoom", "--skip", "motion", "--format", "json",
               "--markdown", str(out) + ".md", "--html", str(out) + ".html", "--json", str(out) + ".json",
               cwd=tmp_path)
    assert bad.returncode == 1, bad.stderr
    data = json.loads(bad.stdout)
    assert [p["url"].rsplit("/", 1)[-1] for p in data["pages"]] == ["bad.html", "good.html"]
    assert json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))["failed"] is True
    assert "#### Critical" in (tmp_path / "r.md").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in (tmp_path / "r.html").read_text(encoding="utf-8")

    down = _cli(closed_port_url, "--timeout", "10", cwd=tmp_path)
    assert down.returncode == 2
    assert "ERROR:" in down.stdout


def test_cli_rejects_bad_arguments(tmp_path):
    assert _cli("ftp://example.invalid/", cwd=tmp_path).returncode == 2
    assert _cli("http://127.0.0.1/", "--fail-on", "fatal", cwd=tmp_path).returncode == 2
