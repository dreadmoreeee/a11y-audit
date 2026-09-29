"""JavaScript snippets evaluated in the page for the tool's own checks."""

# Installs window.__a11yAudit with shared helpers. Idempotent.
HELPERS = r"""
() => {
  if (window.__a11yAudit) return true;
  const A = {ids: new WeakMap(), next: 1, snap: new WeakMap()};
  A.id = el => { if (!A.ids.has(el)) A.ids.set(el, A.next++); return A.ids.get(el); };
  A.sel = el => {
    if (!el || el.nodeType !== 1) return '';
    const parts = [];
    let cur = el;
    while (cur && cur.nodeType === 1 && parts.length < 7) {
      if (cur.id) {
        const esc = '#' + CSS.escape(cur.id);
        let unique = false;
        try { unique = document.querySelectorAll(esc).length === 1; } catch (e) { unique = false; }
        if (unique) { parts.unshift(esc); break; }
      }
      const tag = cur.localName;
      if (tag === 'html' || tag === 'body') { parts.unshift(tag); break; }
      let s = tag;
      const p = cur.parentElement;
      if (p) {
        const same = Array.from(p.children).filter(c => c.localName === tag);
        if (same.length > 1) s += ':nth-of-type(' + (same.indexOf(cur) + 1) + ')';
      }
      parts.unshift(s);
      cur = p;
    }
    return parts.join(' > ');
  };
  A.text = el => {
    const t = (el.getAttribute && el.getAttribute('aria-label')) || el.innerText || el.value || el.title || '';
    return String(t).trim().replace(/\s+/g, ' ').slice(0, 60);
  };
  A.snippet = el => (el.outerHTML || '').slice(0, 200);
  A.transparent = c => !c || c === 'transparent' || /rgba\([^)]*,\s*0\)$/.test(c);
  A.visible = el => {
    const r = el.getBoundingClientRect();
    if (r.width <= 2 || r.height <= 2) return false;
    const cs = getComputedStyle(el);
    return cs.visibility !== 'hidden' && cs.display !== 'none' && parseFloat(cs.opacity) > 0;
  };
  A.style = el => {
    const parts = [];
    for (const pseudo of [null, '::before', '::after']) {
      const cs = getComputedStyle(el, pseudo);
      if (pseudo && (cs.content === 'none' || cs.content === 'normal')) { parts.push('-'); continue; }
      const ow = parseFloat(cs.outlineWidth) || 0;
      const outline = (cs.outlineStyle === 'none' || ow === 0 || A.transparent(cs.outlineColor))
        ? 'none' : [cs.outlineStyle, cs.outlineWidth, cs.outlineColor, cs.outlineOffset].join(' ');
      parts.push([outline, cs.boxShadow, cs.borderTopColor, cs.borderRightColor, cs.borderBottomColor,
        cs.borderLeftColor, cs.borderTopWidth, cs.borderBottomWidth, cs.backgroundColor, cs.backgroundImage,
        cs.color, cs.textDecorationLine, cs.opacity, cs.transform, cs.filter].join('|'));
    }
    return parts.join('||');
  };
  // Elements whose style may carry the focus indicator of el.
  A.proxies = el => {
    const out = [el];
    const p = el.parentElement;
    if (p) { out.push(p); if (p.parentElement) out.push(p.parentElement); }
    if (el.previousElementSibling) out.push(el.previousElementSibling);
    if (el.nextElementSibling) out.push(el.nextElementSibling);
    for (const lab of Array.from(el.labels || [])) { out.push(lab); out.push(...Array.from(lab.children)); }
    return out;
  };
  A.fixed = el => {
    for (let c = el; c && c.nodeType === 1; c = c.parentElement) {
      const p = getComputedStyle(c).position;
      if (p === 'fixed' || p === 'sticky') return true;
    }
    return false;
  };
  window.__a11yAudit = A;
  return true;
}
"""

# Records unfocused styles of every tabbable element (and two ancestors),
# clears focus and returns the number of tabbable elements.
FOCUS_SNAPSHOT = r"""
() => {
  const A = window.__a11yAudit;
  const Q = 'a[href],area[href],button,input,select,textarea,iframe,summary,[tabindex],' +
            '[contenteditable=""],[contenteditable="true"],audio[controls],video[controls]';
  const els = Array.from(document.querySelectorAll(Q)).filter(el => {
    if (el.disabled || el.tabIndex < 0 || el.type === 'hidden') return false;
    if (el.closest('[inert]')) return false;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') return false;
    return el.getClientRects().length > 0;
  });
  const snapOne = el => { if (el && el.nodeType === 1 && !A.snap.has(el)) A.snap.set(el, A.style(el)); };
  for (const el of els) for (const c of A.proxies(el)) snapOne(c);
  if (document.activeElement && document.activeElement !== document.body && document.activeElement.blur) {
    document.activeElement.blur();
  }
  window.scrollTo(0, 0);
  return els.length;
}
"""

# Describes the currently focused element after a Tab press.
FOCUS_STEP = r"""
() => {
  const A = window.__a11yAudit;
  let el = document.activeElement;
  while (el && el.shadowRoot && el.shadowRoot.activeElement) el = el.shadowRoot.activeElement;
  if (!el || el === document.body || el === document.documentElement) return {id: 0, body: true};
  const r = el.getBoundingClientRect();
  const vw = document.documentElement.clientWidth, vh = window.innerHeight;
  const cs = getComputedStyle(el);
  const zero = r.width * r.height <= 4 || parseFloat(cs.opacity) === 0 || cs.visibility === 'hidden';
  const offscreen = r.right <= 0 || r.bottom <= 0 || r.left >= vw || r.top >= vh;
  let indicator = null;
  let proxy = null;
  A.proxies(el).forEach((c, i) => {
    const before = A.snap.get(c);
    if (before === undefined) return;
    const changed = A.style(c) !== before;
    if (i < 3 && c !== el.previousElementSibling && c !== el.nextElementSibling) {
      indicator = indicator === true ? true : changed;
    } else {
      proxy = proxy === true ? true : changed;
    }
  });
  return {
    id: A.id(el), body: false, selector: A.sel(el), tag: el.localName, text: A.text(el),
    html: A.snippet(el), x: Math.round(r.left + window.scrollX), y: Math.round(r.top + window.scrollY),
    w: Math.round(r.width), h: Math.round(r.height), vh: vh, zero: zero, offscreen: offscreen,
    fixed: A.fixed(el), iframe: el.localName === 'iframe', indicator: indicator, proxy: proxy
  };
}
"""

# Motion under prefers-reduced-motion: running animations, movement transitions, smooth scroll.
MOTION = r"""
(opts) => {
  const A = window.__a11yAudit;
  const thr = opts.thresholdMs;
  const running = [];
  const seen = new Set();
  const anims = document.getAnimations ? document.getAnimations() : [];
  for (const an of anims) {
    if (an.playState !== 'running') continue;
    const eff = an.effect;
    if (!eff || !eff.target) continue;
    const t = eff.getComputedTiming();
    const dur = typeof t.duration === 'number' ? t.duration : 0;
    const infinite = t.iterations === Infinity;
    const total = infinite ? Infinity : dur * (t.iterations || 1);
    if (!(total > thr)) continue;
    const target = eff.target;
    if (target.nodeType !== 1 || !A.visible(target)) continue;
    const ctor = an.constructor ? an.constructor.name : '';
    const kind = ctor === 'CSSTransition' ? 'transition' : (ctor === 'CSSAnimation' ? 'animation' : 'script');
    const name = an.animationName || an.transitionProperty || an.id || '';
    const key = A.id(target) + '|' + kind + '|' + name + '|' + (eff.pseudoElement || '');
    if (seen.has(key)) continue;
    seen.add(key);
    running.push({
      selector: A.sel(target) + (eff.pseudoElement || ''), html: A.snippet(target),
      detail: kind + (name ? ' "' + name + '"' : '') + ', ' +
        (infinite ? Math.round(dur) + ' ms x infinite' : Math.round(total) + ' ms')
    });
  }
  const MOVE = /^(transform|translate|scale|rotate|left|top|right|bottom|inset[a-z-]*|margin[a-z-]*|offset[a-z-]*)$/;
  const secs = s => { s = s.trim(); return s.endsWith('ms') ? parseFloat(s) : parseFloat(s) * 1000; };
  const transitions = [];
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (!cs.transitionDuration || cs.transitionDuration === '0s') continue;
    const props = cs.transitionProperty.split(',').map(s => s.trim());
    const durs = cs.transitionDuration.split(',').map(secs);
    for (let i = 0; i < props.length; i++) {
      const d = durs[i % durs.length];
      if (d > thr && MOVE.test(props[i])) {
        if (!A.visible(el)) break;
        transitions.push({selector: A.sel(el), html: A.snippet(el), detail: props[i] + ' ' + Math.round(d) + ' ms'});
        break;
      }
    }
  }
  const smooth = [];
  for (const el of [document.documentElement, document.body]) {
    if (el && getComputedStyle(el).scrollBehavior === 'smooth') {
      smooth.push({selector: el.localName, html: '', detail: 'scroll-behavior: smooth'});
    }
  }
  return {running: running, transitions: transitions, smooth: smooth};
}
"""

# Scales every font size (and px line-heights) by opts.factor and reports
# new horizontal overflow, clipped text containers and text pushed off-screen.
# Phase 'before' stores the baseline, phase 'apply' scales, phase 'after' measures.
TEXT_ZOOM = r"""
(opts) => {
  const A = window.__a11yAudit;
  const root = document.documentElement;
  const hides = v => v === 'hidden' || v === 'clip';
  const hasText = el => {
    for (const n of el.childNodes) if (n.nodeType === 3 && n.textContent.trim()) return true;
    return false;
  };
  const clipped = () => {
    const out = new Map();
    for (const el of document.body.querySelectorAll('*')) {
      const cs = getComputedStyle(el);
      const hx = hides(cs.overflowX), hy = hides(cs.overflowY);
      const ellipsis = cs.textOverflow === 'ellipsis';
      if (!hx && !hy && !ellipsis) continue;
      if (!A.visible(el)) continue;
      const txt = el.innerText;
      if (!txt || !txt.trim()) continue;
      const cx = (hx || ellipsis) && el.scrollWidth > el.clientWidth + 2;
      const cy = hy && el.scrollHeight > el.clientHeight + 2;
      if (cx || cy) out.set(el, (cx ? 'width' : '') + (cx && cy ? '+' : '') + (cy ? 'height' : ''));
    }
    return out;
  };
  const offscreen = vw => {
    const out = new Set();
    for (const el of document.body.querySelectorAll('*')) {
      if (!hasText(el) || !A.visible(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.right > vw + 2 || r.left < -2) out.add(el);
    }
    return out;
  };
  // True when an ancestor below <body> clips or scrolls horizontally, so el cannot widen the page.
  const contained = el => {
    for (let p = el.parentElement; p && p !== document.body && p !== root; p = p.parentElement) {
      if (getComputedStyle(p).overflowX !== 'visible') return true;
    }
    return false;
  };
  const beyond = vw => {
    const out = new Set();
    for (const el of document.body.querySelectorAll('*')) {
      if (el.getBoundingClientRect().right > vw + 2) out.add(el);
    }
    return out;
  };
  if (opts.phase === 'before') {
    window.scrollTo(0, 0);
    A.zoomBase = {
      scrollWidth: root.scrollWidth, clientWidth: root.clientWidth,
      clipped: clipped(), offscreen: offscreen(root.clientWidth), beyond: beyond(root.clientWidth)
    };
    return {scrollWidth: root.scrollWidth, clientWidth: root.clientWidth};
  }
  if (opts.phase === 'apply') {
    const els = [root].concat(Array.from(document.querySelectorAll('body, body *')))
      .filter(el => !el.closest('svg') && !['script', 'style', 'noscript', 'template'].includes(el.localName));
    const sizes = els.map(el => { const cs = getComputedStyle(el); return [el, parseFloat(cs.fontSize), cs.lineHeight]; });
    for (const [el, fs, lh] of sizes) {
      if (!fs) continue;
      el.style.setProperty('font-size', (fs * opts.factor) + 'px', 'important');
      if (lh.endsWith('px')) el.style.setProperty('line-height', (parseFloat(lh) * opts.factor) + 'px', 'important');
    }
    return sizes.length;
  }
  const base = A.zoomBase;
  const vw = root.clientWidth;
  const result = {scrollWidth: root.scrollWidth, clientWidth: vw, overflow: [], clipped: [], offscreen: []};
  if (root.scrollWidth > vw + 2 && root.scrollWidth > base.scrollWidth + 2) {
    for (const el of document.body.querySelectorAll('*')) {
      if (base.beyond.has(el) || !A.visible(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.right <= vw + 2 || contained(el)) continue;
      const p = el.parentElement;
      if (p && p !== document.body && p.getBoundingClientRect().right > vw + 2) continue;
      result.overflow.push({selector: A.sel(el), html: A.snippet(el),
        detail: 'right edge at ' + Math.round(r.right) + ' px, viewport ' + vw + ' px'});
    }
    if (!result.overflow.length) {
      result.overflow.push({selector: 'html', html: '', detail: 'document ' + root.scrollWidth + ' px wide, viewport ' + vw + ' px'});
    }
  }
  const now = clipped();
  for (const [el, how] of now) {
    if (base.clipped.has(el)) continue;
    let nested = false;
    for (let p = el.parentElement; p; p = p.parentElement) if (now.has(p) && !base.clipped.has(p)) { nested = true; break; }
    if (nested) continue;
    result.clipped.push({selector: A.sel(el), html: A.snippet(el), detail: 'content clipped in ' + how});
  }
  if (root.scrollWidth <= vw + 2) {
    for (const el of offscreen(vw)) {
      if (base.offscreen.has(el)) continue;
      result.offscreen.push({selector: A.sel(el), html: A.snippet(el), detail: 'text outside the viewport'});
    }
  }
  return result;
}
"""
