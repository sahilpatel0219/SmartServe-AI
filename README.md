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

- **Themes:** **dark (default) — "Noir Crimson"** (crimson accent) and
  **light — "Indigo"** (indigo accent, deliberately not red so light-mode red
  alerts never collide with the brand). Switch via `data-theme` on `<html>`.
- **Single source of truth:** [`static/css/theme.css`](static/css/theme.css) —
  all color, spacing, radius, shadow, blur, and type are CSS custom properties;
  no component hardcodes a hex outside this file. Color/shadow tokens are
  theme-scoped (`[data-theme="dark"]` / `[data-theme="light"]`); type, spacing,
  radius, and motion tokens (plus legacy `--color-*` aliases) live on `:root`.
- **Type system:** one sans-serif system — **Inter Tight** (display) + **Inter**
  (body); no serif anywhere; tabular numerals on all data. Weights and a fluid
  `clamp()` scale are tokenized (`--fw-*`, `--fs-*`).
- **Theme toggle:** top-bar button (and on `/styleguide`) — persists to
  `localStorage['smartserve-theme']`; defaults to the saved choice, else the OS
  `prefers-color-scheme`, else dark. A pre-paint script prevents FOUC; charts
  re-theme on toggle via `applyChartTheme()`.
- **Motion:** [`static/js/motion.js`](static/js/motion.js) — KPI count-up and
  scroll reveal; disabled by the OS setting or the in-app **Reduce motion**
  toggle (sidebar).
- **Accessibility:** light-mode colors verified WCAG AA; visible focus rings in
  both themes; status always icon + label, never color alone.
- **Live reference:** run the app and open **`/styleguide`** (has a theme toggle)
  to view every component in either theme. Full docs in
  [STYLEGUIDE.md](STYLEGUIDE.md).
