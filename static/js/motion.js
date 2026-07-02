/* ============================================================
   SmartServe AI — Motion Layer
   GPU-friendly only (transform / opacity). Every effect follows the
   OS-level prefers-reduced-motion setting only — there is no in-app
   override. When motion is off, content is shown instantly with no
   animation.
   ============================================================ */
(function () {
  'use strict';

  const motionOff = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // If motion is disabled, reveal any opt-in elements immediately and stop.
  if (motionOff) {
    document.addEventListener('DOMContentLoaded', () => {
      document.querySelectorAll('[data-reveal]').forEach(el => el.classList.add('revealed'));
    });
    return;
  }

  // ── KPI count-up ────────────────────────────────────────────
  // Animates real, server-rendered values from 0 → value, preserving any
  // currency prefix (₹/$), thousands grouping (en-IN), and suffix (%, /100).
  // Non-numeric values (e.g. the "—" empty-state) are left untouched.
  function animateCount(el) {
    const raw = el.textContent.trim();
    const m = raw.match(/^([^\d-]*)(-?[\d,]*\.?\d+)(.*)$/);
    if (!m) return;
    const prefix = m[1], suffix = m[3];
    const target = parseFloat(m[2].replace(/,/g, ''));
    if (!isFinite(target)) return;
    const hasDecimal = m[2].includes('.');
    const dur = 900, start = performance.now();

    const fmt = n => {
      const v = hasDecimal ? Number(n.toFixed(1)) : Math.round(n);
      return prefix + v.toLocaleString('en-IN') + suffix;
    };
    const tick = now => {
      const p = Math.min((now - start) / dur, 1);
      const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
      el.textContent = fmt(target * eased);
      if (p < 1) requestAnimationFrame(tick);
      else el.textContent = raw; // restore exact original formatting
    };
    requestAnimationFrame(tick);
  }

  // ── Scroll reveal + count-up trigger ───────────────────────
  // A manual viewport scan (getBoundingClientRect) drives both effects. This is
  // intentionally used instead of IntersectionObserver: it is simpler, fires
  // reliably in every environment, and guarantees content can never get stuck
  // invisible. Each element is processed once.
  function inView(el) {
    const r = el.getBoundingClientRect();
    return r.top < (window.innerHeight - 40) && r.bottom > 0;
  }

  function scan() {
    document.querySelectorAll('[data-reveal]:not(.revealed)').forEach(el => {
      if (inView(el)) el.classList.add('revealed');
    });
    document.querySelectorAll('.stat-value:not([data-counted]), .stat-card-value:not([data-counted])').forEach(el => {
      if (inView(el)) { el.setAttribute('data-counted', '1'); animateCount(el); }
    });
  }

  window.addEventListener('scroll', scan, { passive: true });
  window.addEventListener('resize', scan, { passive: true });
  document.addEventListener('DOMContentLoaded', scan);
  scan(); // initial pass (covers above-the-fold content immediately)

  // ── Branded crimson progress for the "Analyze My Business" run ─
  // When the analysis form is submitted, show an indeterminate crimson bar.
  document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('analyzeForm');
    const bar  = document.getElementById('analyzeProgress');
    if (form && bar) {
      form.addEventListener('submit', () => { bar.style.display = 'block'; });
    }
  });
})();
