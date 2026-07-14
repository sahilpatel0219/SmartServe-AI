/* ============================================================
   SmartServe AI — Landing interactions
   Scroll-reveal + count-up via IntersectionObserver, smooth anchor
   scrolling, and the mobile nav drawer. GPU-friendly (transform/
   opacity). Honors prefers-reduced-motion: reveals everything
   instantly, skips count-up and smooth-scroll. A manual fallback
   scan guarantees content is never stuck hidden if IO misfires.
   ============================================================ */
(function () {
  'use strict';

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function revealAll() {
    document.querySelectorAll('.lp-reveal').forEach(el => el.classList.add('revealed'));
  }

  // Count 0 → current value, preserving prefix (₹) / grouping / suffix (+, %),
  // then restore the exact server-rendered text. Mirrors the app's count-up.
  function countUp(el) {
    const raw = el.textContent.trim();
    const m = raw.match(/^([^\d-]*)(-?[\d,]*\.?\d+)(.*)$/);
    if (!m) return;
    const prefix = m[1], suffix = m[3], target = parseFloat(m[2].replace(/,/g, ''));
    if (!isFinite(target)) return;
    const dur = 1000, start = performance.now();
    function tick(now) {
      const p = Math.min((now - start) / dur, 1);
      const e = 1 - Math.pow(1 - p, 3);
      el.textContent = prefix + Math.round(target * e).toLocaleString('en-IN') + suffix;
      if (p < 1) requestAnimationFrame(tick);
      else el.textContent = raw;
    }
    requestAnimationFrame(tick);
  }

  document.addEventListener('DOMContentLoaded', function () {
    // ── Mobile nav drawer ─────────────────────────────────────
    const nav = document.getElementById('lpNav');
    const toggle = document.getElementById('lpNavToggle');
    if (nav && toggle) {
      toggle.addEventListener('click', function () {
        const open = nav.classList.toggle('is-open');
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
      nav.querySelectorAll('.lp-nav__links a').forEach(a =>
        a.addEventListener('click', function () {
          nav.classList.remove('is-open');
          toggle.setAttribute('aria-expanded', 'false');
        })
      );
    }

    // ── Smooth anchor scroll (instant under reduced motion) ───
    document.querySelectorAll('a[href^="#"]').forEach(a => {
      a.addEventListener('click', function (e) {
        const id = a.getAttribute('href');
        if (!id || id.length < 2) return;
        const tgt = document.querySelector(id);
        if (!tgt) return;
        e.preventDefault();
        const y = tgt.getBoundingClientRect().top + window.pageYOffset - 72;
        window.scrollTo({ top: y, behavior: reduce ? 'auto' : 'smooth' });
      });
    });

    // File-load failsafe (set by the inline pre-paint script) is now moot.
    if (window.__lpFallback) { clearTimeout(window.__lpFallback); }

    // Entrance failsafe: guarantee the load-sequence elements end up fully
    // visible even if the CSS animation clock never advances (throttled tabs,
    // some headless renderers). Real browsers finish the ~0.7s entrance first,
    // so this is a harmless no-op there.
    const settle = () => document.documentElement.classList.add('lp-entered');
    if (reduce) { settle(); revealAll(); return; }  // instant, no animation
    setTimeout(settle, 1600);

    // ── IntersectionObserver: reveal + count-up ───────────────
    let io = null;
    if ('IntersectionObserver' in window) {
      io = new IntersectionObserver(function (entries, obs) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          const el = en.target;
          el.classList.add('revealed');
          if (el.classList.contains('lp-count') && !el.dataset.counted) { el.dataset.counted = '1'; countUp(el); }
          el.querySelectorAll('.lp-count:not([data-counted])').forEach(function (c) { c.dataset.counted = '1'; countUp(c); });
          obs.unobserve(el);
        });
      }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
      document.querySelectorAll('.lp-reveal, .lp-count').forEach(el => io.observe(el));
    } else {
      revealAll();
      document.querySelectorAll('.lp-count').forEach(c => { c.dataset.counted = '1'; countUp(c); });
    }

    // ── Fallback scan (belt-and-suspenders) ───────────────────
    function fallbackScan() {
      document.querySelectorAll('.lp-reveal:not(.revealed)').forEach(function (el) {
        const r = el.getBoundingClientRect();
        if (r.top < window.innerHeight - 40 && r.bottom > 0) { el.classList.add('revealed'); if (io) io.unobserve(el); }
      });
      document.querySelectorAll('.lp-count:not([data-counted])').forEach(function (el) {
        const r = el.getBoundingClientRect();
        if (r.top < window.innerHeight - 40 && r.bottom > 0) { el.dataset.counted = '1'; countUp(el); if (io) io.unobserve(el); }
      });
    }
    window.addEventListener('scroll', fallbackScan, { passive: true });
    setTimeout(fallbackScan, 1400);

    // Last-resort safety: if neither IO nor scroll ever fire (throttled/headless
    // renderers) — or the reveal transition itself is throttled — reveal
    // everything AND skip the transition, so no section can stay hidden. Real
    // browsers reveal on scroll well before this; count values are already in
    // the DOM, so numbers read correctly whether or not count-up runs.
    setTimeout(function () {
      revealAll();
      document.documentElement.classList.add('lp-force-visible');
    }, 3500);
  });
})();
