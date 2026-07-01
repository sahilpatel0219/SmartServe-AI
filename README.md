# SmartServe AI

An AI-powered operating system for food businesses — orders, inventory, staff,
analytics, and machine learning in one platform. Built with Django + a hybrid
SQLite/MongoDB data layer. All AI predictions, forecasts, insights, and health
scores are computed **only from each business's own uploaded data** (strict
multi-tenant isolation; no mock or seeded data).

For installation, environment, and architecture, see [SETUP.md](SETUP.md).

---

## Design system — "Noir Crimson"

The UI uses a dark, premium design system: near-black canvas, a single glowing
crimson accent, tight grotesk headlines (Inter Tight), glassmorphic depth, and
motion that respects `prefers-reduced-motion`. **This supersedes the previous
green/amber palette.**

- **Single source of truth:** [`static/css/theme.css`](static/css/theme.css) —
  all color, spacing, radius, shadow, blur, and type are CSS custom properties;
  no component hardcodes a hex outside this file. Legacy `--color-*` token names
  are aliased to the new values for backward compatibility.
- **Fonts:** Inter Tight (display) + Inter (body), loaded in `base.html`.
- **Motion:** [`static/js/motion.js`](static/js/motion.js) — KPI count-up and
  scroll reveal; disabled by the OS setting or the in-app **Reduce motion**
  toggle (sidebar → Settings).
- **Theme:** dark is the default and only built theme; light is structurally
  possible later but not built.
- **Live reference:** run the app and open **`/styleguide`** to view every
  component and state. Full docs in [STYLEGUIDE.md](STYLEGUIDE.md).
