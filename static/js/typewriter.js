/* ============================================================
   SmartServe AI — Typewriter (landing hero subline only)
   Types + erases a rotating word inside one line. GPU-friendly
   (text only), no layout shift (a hidden sizer reserves the box),
   and fully accessible:
     - the complete phrase lives in a .sr-only sibling for AT
     - the animated element is aria-hidden
     - prefers-reduced-motion → render the first word instantly,
       no caret, no typing.
   Markup expected:
     <span class="lp-typer" data-words='["a","b"]'
           data-type-speed="45" data-erase-speed="28" data-hold="1400"
           aria-hidden="true">
       <span class="lp-typer__sizer">longest word</span>
       <span class="lp-typer__text"></span>
     </span>
   ============================================================ */
(function () {
  'use strict';

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function init(el) {
    let words;
    try { words = JSON.parse(el.getAttribute('data-words') || '[]'); }
    catch (e) { words = []; }
    if (!words.length) return;

    const textEl = el.querySelector('.lp-typer__text');
    if (!textEl) return;

    // Reduced motion (or no rAF): show the first word instantly, drop the caret.
    if (reduce) {
      textEl.textContent = words[0];
      el.classList.add('is-static');
      return;
    }

    const typeSpeed  = parseInt(el.getAttribute('data-type-speed')  || '45', 10);
    const eraseSpeed = parseInt(el.getAttribute('data-erase-speed') || '28', 10);
    const hold       = parseInt(el.getAttribute('data-hold')        || '1400', 10);

    let wi = 0, ci = 0, erasing = false;

    function step() {
      const word = words[wi];
      if (!erasing) {
        ci++;
        textEl.textContent = word.slice(0, ci);
        if (ci >= word.length) { erasing = true; setTimeout(step, hold); return; }
        setTimeout(step, typeSpeed);
      } else {
        ci--;
        textEl.textContent = word.slice(0, ci);
        if (ci <= 0) { erasing = false; wi = (wi + 1) % words.length; setTimeout(step, typeSpeed * 3); return; }
        setTimeout(step, eraseSpeed);
      }
    }
    setTimeout(step, 500);
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.lp-typer').forEach(init);
  });
})();
