# a11y-audit

Accessibility audit of web pages in headless Chromium. Runs [axe-core](https://github.com/dequelabs/axe-core)
plus three checks that axe does not cover well: keyboard focus order, 200% text zoom and
`prefers-reduced-motion`. Groups findings by impact and WCAG criterion, writes JSON, Markdown and
self-contained HTML reports, and returns a non-zero exit code for CI.

- One dependency: Playwright (Chromium). axe-core is vendored, no network needed for the engine.
- Only GET page loads. Requests with other methods (form posts, analytics beacons) are blocked.
- Polite by default: at least 1 s between pages, clear User-Agent.

## Install

```
pip install .
python -m playwright install chromium
```

Python 3.10+.

## Usage

```
a11y-audit https://example.com https://example.com/contact --fail-on serious \
    --html report.html --markdown report.md --json report.json
python -m a11y_audit https://example.com --format json
```

| Option | Default | Meaning |
|---|---|---|
| `--fail-on {critical,serious,moderate,minor}` | off | exit 1 if any violation has this impact or worse |
| `-f, --format {text,json,markdown,html}` | text | what is printed to stdout |
| `--json / --markdown / --html PATH` | | also write that report to a file |
| `--max-tabs N` | 30 | Tab presses in the focus sample |
| `--zoom FACTOR` | 2.0 | text scale factor |
| `--motion-threshold-ms MS` | 250 | ignore shorter animations/transitions |
| `--viewport WxH` | 1280x800 | viewport size |
| `--delay S` | 1.0 | minimum seconds between page loads |
| `--skip {axe,motion,focus,zoom}` | | skip a check (repeatable) |
| `--wcag-only` | | axe rules tagged WCAG A/AA only (no best practices) |

Exit codes: `0` ok, `1` violations at or above `--fail-on`, `2` a page could not be audited or bad arguments.

Library use: `from a11y_audit import audit_urls, Options`. See `examples/` for a Python script and a
GitHub Actions job.

## What it checks

| Check | Rule ids | WCAG |
|---|---|---|
| axe-core 4.13 (all rules, tags like `wcag143` mapped to 1.4.3) | axe rule ids | per rule, or "best practice" |
| Keyboard: presses Tab through the first N stops and records the order (listed in HTML report) | | 2.4.3 |
| Focus that never leaves an element or cycles within a subset | `focus-trap` | 2.1.2 |
| No outline/box-shadow/border/background change on focus (element, ancestors, label, siblings) | `focus-not-visible` | 2.4.7 |
| Focused element off-screen or zero-size, re-measured 700 ms later | `focus-offscreen` | 2.4.7, 2.4.11 |
| Tab order jumps more than one viewport back up | `focus-order-jump` | 2.4.3 |
| Text at 200%: new horizontal page scroll | `text-zoom-overflow` | 1.4.4, 1.4.10 |
| Text at 200%: newly clipped text containers (overflow hidden, ellipsis) | `text-zoom-clipped` | 1.4.4 |
| Text at 200%: text pushed outside the viewport | `text-zoom-offscreen` | 1.4.10 |
| Reduced motion emulated: animations still running | `motion-animation-running` | 2.3.3 |
| Reduced motion: transform/position transitions longer than the threshold | `motion-transition` | 2.3.3 |
| Reduced motion: `scroll-behavior: smooth` still on | `motion-smooth-scroll` | 2.3.3 |

Each violation lists impact (critical, serious, moderate, minor), WCAG criteria, element count,
CSS selectors and a short fix hint. The reports also group rules per WCAG criterion.

Limits: automated checks find only part of all accessibility problems. Text zoom is simulated by
doubling every computed font size (and pixel line-heights), close to a browser text-only zoom.
Motion is sampled once after load, so scroll-triggered animations are not seen. The keyboard
sample covers the first N Tab stops only.

## Measured result

Run on 2026-09-29 against the author's own sites (4 page loads per run, 2 s apart, GET only):

```
a11y-audit https://demarkstudio.ca https://demo.demarkstudio.ca https://demo.demarkstudio.ca/riverside-pub/site https://marvin.demarkstudio.ca --delay 2 --fail-on serious --json r.json --markdown examples/measured-report.md --html examples/measured-report.html
```

```
a11y-audit 1.0.0, axe-core 4.13.0, viewport 1280x800, reduced motion emulated, text zoom 200%

https://demarkstudio.ca
  final URL: https://demarkstudio.ca/en/
  critical 0 (0 nodes)  serious 2 (11 nodes)  moderate 0 (0 nodes)  minor 0 (0 nodes)
  Keyboard sample: 30 Tab stops, 30 distinct elements, 85 tabbable on page
  serious   focus-offscreen [2.4.7, 2.4.11] x10  Focused element is off-screen or has zero size
            - #herramientas > div > div:nth-of-type(2) > ul
            - #herramientas > div > div:nth-of-type(2) > ul > li:nth-of-type(1) > article > a
            - #herramientas > div > div:nth-of-type(2) > ul > li:nth-of-type(2) > article > a
            ... 7 more
            fix: Bring focused items into view (scroll carousels to the focused slide, show skip links on :focus) or make hidden ones inert.
  serious   text-zoom-overflow [1.4.4, 1.4.10] x1  Page scrolls horizontally with text at 200%
            - #nav
            fix: Use relative widths (%, rem, max-width) and allow long words to wrap (overflow-wrap:anywhere).

https://demo.demarkstudio.ca
  final URL: https://demo.demarkstudio.ca/app/login
  critical 0 (0 nodes)  serious 0 (0 nodes)  moderate 0 (0 nodes)  minor 0 (0 nodes)
  Keyboard sample: 9 Tab stops, 9 distinct elements, 9 tabbable on page

https://demo.demarkstudio.ca/riverside-pub/site
  critical 0 (0 nodes)  serious 0 (0 nodes)  moderate 1 (1 nodes)  minor 0 (0 nodes)
  Keyboard sample: 30 Tab stops, 30 distinct elements, 40 tabbable on page
  moderate  region [best practice] x1  All page content should be contained by landmarks
            - #anuncio
            fix: Place all content inside landmarks (header, nav, main, footer).

https://marvin.demarkstudio.ca
  final URL: https://marvin.demarkstudio.ca/
  critical 0 (0 nodes)  serious 0 (0 nodes)  moderate 0 (0 nodes)  minor 0 (0 nodes)
  Keyboard sample: 30 Tab stops, 30 distinct elements, 46 tabbable on page

Total: critical 0, serious 2, moderate 1, minor 0 (rules); pages 4, errors 0
fail-on serious: FAILED
```

Exit code 1. What it means:

- axe-core found no WCAG violations on any page; the only axe finding is a best-practice one
  (`#anuncio` outside landmarks on the Riverside Pub demo).
- The own checks found two real problems on demarkstudio.ca. The "Examples of our work" carousel
  is moved with `transform: translateX(-5547px)` inside an `overflow: clip` section, so Tab stops
  18-27 land on slides 200 to 5500 px left of the viewport and the carousel does not follow focus.
  With text at 200% the main navigation (`#nav`) no longer fits: its right edge is at 1671 px in a
  1280 px viewport, so the page scrolls sideways.
- demo.demarkstudio.ca redirects to its login page; only that page was loaded, nothing was submitted.
- No focus traps, no invisible focus and no motion left running under reduced motion on any page.

Full reports from the same run: [examples/measured-report.md](examples/measured-report.md) and
[examples/measured-report.html](examples/measured-report.html).

Tests (local fixture pages on random ports, no internet):

```
python -m pytest -q -p no:cacheprovider --import-mode=importlib C:\Users\marvin\oss-tools3\a11y-audit
26 passed in 27.39s
```

## License notes

`a11y_audit/vendor/axe.min.js` is axe-core 4.13.0 by Deque Systems, shipped unmodified under the
Mozilla Public License 2.0; its license and third-party notices are in
`a11y_audit/vendor/axe-core-LICENSE.txt`. Source: https://github.com/dequelabs/axe-core.
The rest of this project is MIT.

Marvin Palencia, founder of [DeMark Studio](https://demarkstudio.ca), Miramichi, New Brunswick, Canada. Portfolio: [marvin.demarkstudio.ca](https://marvin.demarkstudio.ca)

MIT License. The bundled `a11y_audit/vendor/axe.min.js` is axe-core by Deque Systems, under the Mozilla Public License 2.0 (see `a11y_audit/vendor/axe-core-LICENSE.txt`).
