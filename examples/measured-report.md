# Accessibility audit

a11y-audit 1.0.0, axe-core 4.13.0, viewport 1280x800, reduced motion emulated, text zoom 200%. Generated 2026-09-29T08:45:22+00:00.

| Page | Status | Critical | Serious | Moderate | Minor |
|---|---|---:|---:|---:|---:|
| https://demarkstudio.ca | 200 | 0 | 2 | 0 | 0 |
| https://demo.demarkstudio.ca | 200 | 0 | 0 | 0 | 0 |
| https://demo.demarkstudio.ca/riverside-pub/site | 200 | 0 | 0 | 1 | 0 |
| https://marvin.demarkstudio.ca | 200 | 0 | 0 | 0 | 0 |

Counts are rules; each rule may affect several elements.

**fail-on serious: FAILED**

## https://demarkstudio.ca

Title: DeMark — Websites, online booking and invoicing for small businesses across Canada  
axe: 0 violations, 41 passes, 1 need review  
Keyboard sample: 30 Tab stops, 30 distinct elements, 85 tabbable on page

### By WCAG criterion

| Criterion | Rules | Elements |
|---|---|---:|
| 1.4.4 Resize Text | text-zoom-overflow | 1 |
| 1.4.10 Reflow | text-zoom-overflow | 1 |
| 2.4.7 Focus Visible | focus-offscreen | 10 |
| 2.4.11 Focus Not Obscured (Minimum) | focus-offscreen | 10 |

### Violations by impact

#### Serious

- **focus-offscreen** (a11y-audit, WCAG 2.4.7, 2.4.11, 10 elements): Focused element is off-screen or has zero size
  - Fix: Bring focused items into view (scroll carousels to the focused slide, show skip links on :focus) or make hidden ones inert.
  - `#herramientas > div > div:nth-of-type(2) > ul` - off screen (Tab stop 18)
  - `#herramientas > div > div:nth-of-type(2) > ul > li:nth-of-type(1) > article > a` - off screen (Tab stop 19)
  - `#herramientas > div > div:nth-of-type(2) > ul > li:nth-of-type(2) > article > a` - off screen (Tab stop 20)
  - `#herramientas > div > div:nth-of-type(2) > ul > li:nth-of-type(3) > article > a` - off screen (Tab stop 21)
  - `#herramientas > div > div:nth-of-type(2) > ul > li:nth-of-type(4) > article > a` - off screen (Tab stop 22)
  - `#herramientas > div > div:nth-of-type(2) > ul > li:nth-of-type(5) > article > a` - off screen (Tab stop 23)
  - `#herramientas > div > div:nth-of-type(2) > ul > li:nth-of-type(6) > article > a` - off screen (Tab stop 24)
  - `#herramientas > div > div:nth-of-type(2) > ul > li:nth-of-type(7) > article > a` - off screen (Tab stop 25)
  - `#herramientas > div > div:nth-of-type(2) > ul > li:nth-of-type(8) > article > a` - off screen (Tab stop 26)
  - `#herramientas > div > div:nth-of-type(2) > ul > li:nth-of-type(9) > article > a` - off screen (Tab stop 27)

- **text-zoom-overflow** (a11y-audit, WCAG 1.4.4, 1.4.10, 1 element): Page scrolls horizontally with text at 200%
  - Fix: Use relative widths (%, rem, max-width) and allow long words to wrap (overflow-wrap:anywhere).
  - `#nav` - right edge at 1671 px, viewport 1280 px

## https://demo.demarkstudio.ca

Title: Sign in — DeMark  
axe: 0 violations, 29 passes, 0 need review  
Keyboard sample: 9 Tab stops, 9 distinct elements, 9 tabbable on page

No violations found.

## https://demo.demarkstudio.ca/riverside-pub/site

Title: Riverside Pub & Coasters Lounge — Good food, cold drinks, live music  
axe: 1 violations, 32 passes, 1 need review  
Keyboard sample: 30 Tab stops, 30 distinct elements, 40 tabbable on page

### By WCAG criterion

| Criterion | Rules | Elements |
|---|---|---:|
| Best practice (no WCAG criterion) | region | 1 |

### Violations by impact

#### Moderate

- **region** (axe, WCAG best practice, 1 element): All page content should be contained by landmarks
  - Fix: Place all content inside landmarks (header, nav, main, footer).
  - `#anuncio` - Some page content is not contained by landmarks

## https://marvin.demarkstudio.ca

Title: Marvin Palencia — Python & Web Developer \| Stripe, FastAPI, Websites  
axe: 0 violations, 36 passes, 0 need review  
Keyboard sample: 30 Tab stops, 30 distinct elements, 46 tabbable on page

No violations found.
