"""Command line interface: a11y-audit URL [URL ...]."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .engine import CHECKS, DEFAULT_USER_AGENT, Options
from .report import RENDERERS
from .rules import IMPACTS

EXIT_OK, EXIT_FAIL, EXIT_ERROR = 0, 1, 2


def _viewport(value):
    try:
        w, h = value.lower().split("x")
        w, h = int(w), int(h)
        if w < 200 or h < 200:
            raise ValueError
        return (w, h)
    except ValueError:
        raise argparse.ArgumentTypeError("expected WIDTHxHEIGHT, e.g. 1280x800")


def _url(value):
    if not value.startswith(("http://", "https://")):
        raise argparse.ArgumentTypeError("URL must start with http:// or https://: %r" % value)
    return value


def build_parser():
    p = argparse.ArgumentParser(
        prog="a11y-audit",
        description="Accessibility audit of web pages in headless Chromium: axe-core plus keyboard "
                    "focus order, 200%% text zoom and prefers-reduced-motion checks.")
    p.add_argument("urls", nargs="+", type=_url, metavar="URL", help="page(s) to audit")
    p.add_argument("-f", "--format", choices=sorted(RENDERERS), default="text",
                   help="format printed to stdout (default: text)")
    p.add_argument("--json", metavar="PATH", help="also write the JSON report to PATH")
    p.add_argument("--markdown", "--md", metavar="PATH", dest="markdown", help="also write a Markdown report")
    p.add_argument("--html", metavar="PATH", help="also write a self-contained HTML report")
    p.add_argument("--fail-on", choices=IMPACTS, metavar="{critical,serious,moderate,minor}",
                   help="exit 1 if any violation has this impact or worse")
    p.add_argument("--max-tabs", type=int, default=30, metavar="N",
                   help="Tab presses in the focus-order sample (default: 30)")
    p.add_argument("--motion-threshold-ms", type=int, default=250, metavar="MS",
                   help="ignore animations/transitions at or below this duration (default: 250)")
    p.add_argument("--zoom", type=float, default=2.0, metavar="FACTOR", help="text scale factor (default: 2.0)")
    p.add_argument("--viewport", type=_viewport, default=(1280, 800), metavar="WxH",
                   help="viewport size (default: 1280x800)")
    p.add_argument("--timeout", type=float, default=30.0, metavar="S", help="page load timeout (default: 30)")
    p.add_argument("--delay", type=float, default=1.0, metavar="S",
                   help="minimum seconds between page loads (default: 1.0)")
    p.add_argument("--skip", action="append", choices=CHECKS, default=[],
                   help="skip a check; repeatable")
    p.add_argument("--wcag-only", action="store_true", help="run only axe rules tagged with WCAG A/AA")
    p.add_argument("--max-nodes", type=int, default=10, metavar="N",
                   help="elements listed per violation (default: 10)")
    p.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="User-Agent header")
    p.add_argument("-q", "--quiet", action="store_true", help="no progress messages on stderr")
    p.add_argument("--version", action="version", version="a11y-audit %s" % __version__)
    return p


def _write(path, text):
    if path == "-":
        sys.stdout.write(text)
        return
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def main(argv=None):
    args = build_parser().parse_args(argv)
    opts = Options(
        max_tabs=args.max_tabs, motion_threshold_ms=args.motion_threshold_ms, zoom_factor=args.zoom,
        viewport=args.viewport, timeout_s=args.timeout, delay_s=max(0.0, args.delay),
        user_agent=args.user_agent, skip=list(args.skip), best_practice=not args.wcag_only,
        max_nodes=max(1, args.max_nodes), fail_on=args.fail_on,
    )
    from .engine import audit_urls

    log = None if args.quiet else (lambda msg: print(msg, file=sys.stderr, flush=True))
    report = audit_urls(args.urls, opts, log=log)
    sys.stdout.write(RENDERERS[args.format](report))
    for fmt, path in (("json", args.json), ("markdown", args.markdown), ("html", args.html)):
        if path:
            _write(path, RENDERERS[fmt](report))
    if report["errors"]:
        return EXIT_ERROR
    return EXIT_FAIL if report["failed"] else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
