/* /assets/slideshow.js — drop-in with data-src (manifest.json) + data-slides + data-files */

const UKPA_SLIDESHOW_DEBUG = false; // set true to see alerts while debugging

function report(msg, extra) {
  console.error('[slideshow]', msg, extra || '');
  if (UKPA_SLIDESHOW_DEBUG) alert(`[slideshow] ${msg}`);
}

// Optional: parse JSON provided in a child <script type="application/json" class="ukpa-slides-data">
function parseSlidesFromScriptTag(wrap) {
  const s = wrap.querySelector('.ukpa-slides-data[type="application/json"]');
  if (!s) return null;
  try {
    const txt = s.textContent || s.innerText || '';
    const arr = JSON.parse(txt);
    if (Array.isArray(arr) && arr.length) return arr.filter(x => x && x.src);
  } catch (e) {
    report('Invalid JSON inside <script class="ukpa-slides-data">');
    console.error(e);
  }
  return null;
}

// Parse slides from data attributes (CSV or inline JSON)
function parseSlidesFromDataAttrs(wrap) {
  // CSV: data-files="one.svg,two.svg" (+ optional data-base="/images/slides/")
  const csv = wrap.getAttribute('data-files');
  if (csv !== null) {
    const base = (wrap.getAttribute('data-base') || '').replace(/\/?$/, '/');
    const files = csv.split(',').map(s => s.trim()).filter(Boolean);
    if (!files.length) { report('data-files is present but empty'); return []; }
    return files.map((name, idx) => ({
      src: base && !name.startsWith('/') ? base + name : name,
      alt: `Slide ${idx + 1}`
    }));
  }

  // Inline JSON: data-slides='[{"src":"/x.svg","alt":"…"}, …]'
  const json = wrap.getAttribute('data-slides');
  if (json !== null) {
    try {
      const arr = JSON.parse(json);
      if (!Array.isArray(arr) || !arr.length) { report('data-slides parsed but empty'); return []; }
      return arr.filter(s => s && s.src).map((s, i) => ({ src: s.src, alt: s.alt || `Slide ${i+1}` }));
    } catch (e) {
      report('Invalid JSON in data-slides (see console)');
      console.error('data-slides value:', json, e);
      return [];
    }
  }

  // Child <script> JSON (optional)
  const fromScript = parseSlidesFromScriptTag(wrap);
  if (fromScript) return fromScript;

  return [];
}

// Render + wire up a slideshow given a slide array
function initWithSlides(wrap, slides) {
  if (!slides || !slides.length) { report('No slides available for this slideshow instance.'); return; }

  const img  = wrap.querySelector('.ukpa-slide-img');
  const next = wrap.querySelector('.ukpa-slide-next');
  const cEl  = wrap.querySelector('.ukpa-slide-count');
  const tEl  = wrap.querySelector('.ukpa-slide-total');

  if (!img) { report('Missing .ukpa-slide-img inside slideshow wrapper'); return; }
  if (tEl) tEl.textContent = String(slides.length);

  let i = 0;

  const show = (idx) => {
    const s = slides[idx]; if (!s) return;
    img.src = s.src;
    img.alt = s.alt || `Slide ${idx + 1}`;
    if (cEl) cEl.textContent = String(idx + 1);
  };

  // Report image load failures
  img.addEventListener('error', () => report('Image failed to load: ' + img.src));

  show(i);

  // Advance/Back
  const advance = () => { i = (i + 1) % slides.length; show(i); };
  const back    = () => { i = (i - 1 + slides.length) % slides.length; show(i); };

  // Click/tap overlay
  next?.addEventListener('click', advance);

  // Keyboard
  wrap.tabIndex = 0;
  wrap.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'Enter') { e.preventDefault(); advance(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); back(); }
  });

  // Basic swipe support
  let sx = 0, sy = 0;
  wrap.addEventListener('touchstart', (e) => {
    const t = e.changedTouches[0]; sx = t.clientX; sy = t.clientY;
  }, { passive: true });
  wrap.addEventListener('touchend', (e) => {
    const t = e.changedTouches[0];
    const dx = t.clientX - sx, dy = t.clientY - sy;
    if (Math.abs(dx) > 30 && Math.abs(dx) > Math.abs(dy)) { dx < 0 ? advance() : back(); }
    else { advance(); }
  }, { passive: true });

  // Preload remaining slides
  slides.slice(1).forEach(s => { const pre = new Image(); pre.src = s.src; });
}

// Initialize from a remote JSON (e.g., images/slides/manifest.json)
async function initFromRemote(wrap, url) {
  try {
    const res = await fetch(url, { credentials: 'same-origin', cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!Array.isArray(data) || !data.length) { report('Remote slides JSON is empty', data); return; }
    initWithSlides(wrap, data.filter(s => s && s.src));
  } catch (e) {
    report('Failed to load remote slides JSON: ' + url);
    console.error(e);
  }
}

// Find and initialize all instances
function initAll() {
  const wraps = document.querySelectorAll('.ukpa-slideshow');
  if (!wraps.length) return;
  wraps.forEach((wrap) => {
    const remote = wrap.getAttribute('data-src');
    if (remote) {
      initFromRemote(wrap, remote);
    } else {
      const slides = parseSlidesFromDataAttrs(wrap);
      if (!slides.length) {
        report('No data-files or data-slides attribute found on slideshow wrapper');
        return;
      }
      initWithSlides(wrap, slides);
    }
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAll);
} else {
  initAll();
}

