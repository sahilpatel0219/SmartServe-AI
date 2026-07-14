# SmartServe AI

An AI-powered operating system for food businesses — orders, inventory, staff,
analytics, and machine learning in one platform. Built with Django + a hybrid
SQLite/MongoDB data layer. All AI predictions, forecasts, insights, and health
scores are computed **only from each business's own uploaded data** (strict
multi-tenant isolation; no mock or seeded data).

For installation, environment, and architecture, see [SETUP.md](SETUP.md).

---

## Design system

A premium, token-driven design system with **two themes** that share one
structure, type system, and component set — only token values differ. **This
supersedes the previous green/amber palette.**

- **Themes:** **dark (default) — "Ember"** (deep-red `#950101` brand on softened
  near-black-red surfaces) and **light — "Orchard"** (forest-green `#1A5319`
  brand on a mint canvas with white cells). Each keeps a separate functional
  status palette so alerts stay readable (in dark, brand-red and danger-red are
  separated by brightness + fill + icon, never hue alone). Switch via
  `data-theme` on `<html>`.
- **Bento layout:** a modular grid of varied-size rounded cells (`.bento` +
  `.bento-cell` with `.b-2/.b-3/.b-4/.b-6` spans; tokens `--r-cell`,
  `--gap-bento`) leads the expressive screens — the **landing page**
  ([`templates/core/landing.html`](templates/core/landing.html)) and, going
  forward, the dashboards/report. Data-dense screens keep calm tables/forms.
- **Single source of truth:** [`static/css/theme.css`](static/css/theme.css) —
  all color, spacing, radius, shadow, blur, and type are CSS custom properties;
  no component hardcodes a hex outside this file. Color/shadow tokens are
  theme-scoped (`[data-theme="dark"]` / `[data-theme="light"]`); type, spacing,
  radius, and motion tokens (plus legacy `--color-*` aliases) live on `:root`.
- **Type system:** one sans-serif system — **Open Sans** for both display and
  body, loaded via Google Fonts (`font-display:swap` to minimize FOUT). Tabular
  numerals on all data. Weights and a fluid `clamp()` scale are tokenized
  (`--fw-*`, `--fs-*`).
- **"Change Theme" button:** a labeled control (text + moon/sun icon) in the
  sidebar's Settings section — persists to `localStorage['smartserve-theme']`;
  defaults to the saved choice, else the OS `prefers-color-scheme`, else dark.
  A pre-paint script prevents FOUC; charts re-theme on toggle via
  `applyChartTheme()`.
- **Motion:** [`static/js/motion.js`](static/js/motion.js) — KPI count-up and
  scroll reveal. The landing page adds [`typewriter.js`](static/js/typewriter.js)
  (rotating hero word, no layout shift, full phrase in an `.sr-only` for AT) and
  [`landing.js`](static/js/landing.js) (staggered entrance, IntersectionObserver
  scroll-reveal + count-up, smooth anchor scroll, mobile drawer). All motion
  follows the OS `prefers-reduced-motion` setting only (no in-app override) and
  degrades to instant, fully-visible content.
- **Accessibility:** light-mode colors verified WCAG AA; visible focus rings in
  both themes; status always icon + label, never color alone.
- **Live reference:** run the app and open **`/styleguide`** (has a theme toggle)
  to view every component in either theme. Full docs in
  [STYLEGUIDE.md](STYLEGUIDE.md).
