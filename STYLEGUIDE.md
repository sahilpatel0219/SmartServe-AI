# SmartServe AI — Design System

A premium, editorial UI in two themes that share one structure, type system, and
component set — only the token *values* differ:

- **Dark (default) — "Noir Crimson":** near-black canvas, glowing **crimson** accent.
- **Light — "Indigo":** warm-white canvas, **indigo** accent (deliberately not red,
  so light-mode red alerts never collide with the brand).

> **Live reference:** run the app and open **`/styleguide`** (has a theme toggle)
> to see every component and state in either theme.
>
> **Single source of truth:** [`static/css/theme.css`](static/css/theme.css).
> All color, spacing, radius, shadow, blur, and type are CSS custom properties.
> No component hardcodes a hex value outside that file.

## Type system (shared by both themes)

One deliberate sans-serif system — **no serif anywhere**, no stray non-token fonts.

- **Display** `--font-display` = **Helvetica Neue / Helvetica / Arial** — hero, h1–h3,
  big KPI numbers; use `--lh-tight`/`--lh-snug` + `--tracking-tight`.
- **Body** `--font-body` = **Helvetica Neue / Helvetica / Arial** — all UI text,
  tables, forms, captions; `--lh-normal`.
- All system fonts — no web-font loading, no FOUT risk. Windows/Android generally
  lack Helvetica Neue and fall back to Arial, which is near-identical; expect a
  slightly different look across platforms — that's expected, not a bug.
- **Mono** `--font-mono` = JetBrains Mono — **only** for order IDs / raw code.
- Weights: `--fw-regular 400`, `--fw-medium 500`, `--fw-semibold 600`, `--fw-bold 700`,
  `--fw-black 800` (legacy `--fw-normal`/`--fw-semi` aliased).
- Fluid scale (`clamp()`): `--fs-hero`, `--fs-h1`, `--fs-h2`, `--fs-h3`, `--fs-title`,
  `--fs-body`, `--fs-sm`, `--fs-caption`.
- All numeric data uses `font-variant-numeric: tabular-nums` (`.tabular-nums`).
- No `<link>` font loading is needed (system fonts); the pre-paint theme script
  still prevents a theme-color FOUC on load.

---

## 1. Tokens

Token **names are identical across themes**; only values differ. Values live in
`[data-theme="dark"]` and `[data-theme="light"]`; theme-independent tokens (type,
spacing, radius, blur, motion) and the legacy `--color-*`/`--radius-*`/`--shadow-*`
aliases live on `:root`.

### Surfaces
| Token | Dark | Light | Use |
|---|---|---|---|
| `--bg-deep` | `#070708` | `#ECEBE8` | Behind hero/auth |
| `--bg-base` | `#0A0A0B` | `#F7F7F5` | App background |
| `--bg-elev-1` | `#141416` | `#FFFFFF` | Cards, panels, sidebar |
| `--bg-elev-2` | `#1A1A1D` | `#FFFFFF` | Inputs, table headers |
| `--glass-bg` | white /.04 | white /.65 | Glassmorphic surfaces |
| `--hairline` | white /.08 | `#111318` /.08 | Hairline dividers |

### Text (AA verified)
| Token | Dark | Light | Contrast on card (light) |
|---|---|---|---|
| `--text-primary` | `#F4F4F3` | `#14161C` | 18.1 |
| `--text-muted` | `#A1A1AA` | `#565B63` | 6.8 |
| `--text-faint` | `#6B6B73` | `#71767E` | 4.57 |

### Brand & status
The brand is **not** the generic error color. Use `--brand` for interactive chrome
(buttons, links, active nav, highlights) and solid *critical* banners. Use the
**status palette** for data states, deltas, stock levels, and validation. Brand vs.
alert is distinguished by **fill + icon + position**, not hue alone.

| Token | Dark | Light | Use |
|---|---|---|---|
| `--brand` | `#E5392E` (crimson) | `#4F46E5` (indigo) | CTAs, links, active, highlights |
| `--brand-hover` | `#C72A22` | `#4338CA` | Hover |
| `--success` | `#34D399` | `#15803D` | Positive data, up-deltas (AA 5.0) |
| `--warning` | `#FBBF24` | `#B45309` | Caution, "low" (AA 5.0) |
| `--info` | `#60A5FA` | `#2563EB` | Secondary data series (AA 5.2) |
| `--danger` | `#FF5A52` | `#DC2626` | Negative data (AA 4.8) |
| `--critical` | = `--brand` (red) | `#B91C1C` (red) | Solid system-critical banners |

In **light**, brand is indigo and critical/danger are red — cleanly separate. Each
status color has a matching `*-tint` for soft fills; `--focus-ring` and
`--skeleton-base/sheen` are also theme-scoped so focus and shimmer read on both.

### Radius, blur, elevation
`--r-sm 10px` · `--r-md 14px` · `--r-lg 20px` · `--r-pill 999px` · `--blur 20px`
`--shadow-1` (resting) · `--shadow-2` (raised) · `--shadow-glow` (crimson) ·
`--inset-hi` (1px top light-catch on cards).

### Type
- **Display:** `Helvetica Neue` / `Helvetica` / `Arial` (system fonts) — headlines, KPI numbers, titles.
- **Body:** `Helvetica Neue` / `Helvetica` / `Arial`.
- Fluid sizes via `clamp()`: `--fs-hero`, `--fs-page`, `--fs-section`, `--fs-card`.
- Numbers use `font-variant-numeric: tabular-nums` (`.tabular-nums`).
- A single headline word may be set in `--brand` via `.accent` — used sparingly.

### Legacy aliases
The previous design used `--color-*`, `--radius-*`, `--shadow-*`, `--text-*`
names inline in templates. `theme.css` re-points every one of those at the new
Noir Crimson values, so the whole app adopts the theme without rewriting inline
styles. Prefer the canonical tokens above in new code.

---

## 2. Components

Class-driven; all read from tokens. (See `/styleguide` for live examples.)

- **Layout:** `.sidebar` (crimson active indicator bar), `.topbar` (glass,
  sticky, blurred), `.main-content`, `.page-header`.
- **Surfaces:** `.card` (+ `.card-header/.card-body/.card-footer`), `.glass`.
- **KPI:** `.stat-grid`, `.stat-card`, `.stat-icon`, `.stat-value`,
  `.stat-card-change.up/.down`.
- **Feature card:** `.feature-card` (`__icon`, `__title`, `__desc`).
- **Buttons:** `.btn` + `.btn-primary` (brand color, glow on hover) /
  `.btn-secondary` / `.btn-outline` / `.btn-ghost` / `.btn-danger`; sizes
  `.btn-sm/.btn-lg`, `.btn-pill`; `:disabled` (50% opacity, no pointer events).
  Secondary/outline surfaces use dedicated `--btn-secondary-bg` /
  `--btn-outline-border` tokens (not the panel `--glass-*` tokens) so they read
  clearly on both the near-black dark canvas and white light canvas. Motion:
  hover lifts 1px with a brand-tinted glow; `:active` scales to `.97`;
  `:focus-visible` shows a 3px ring in `--focus-ring` (crimson in dark, indigo
  in light) — same timing/easing in both themes, only colors differ.
- **Forms:** `.form-control` (dark field, crimson focus ring),
  `.form-label/.form-group/.form-text`, `.is-invalid/.is-valid`.
- **Badges / pills:** `.badge` + `-success/-warning/-danger/-info/-neutral/-brand`;
  `.status-pill.ok/.warn/.down` (leading dot).
- **Table:** `.data-table` (sticky header, hairline rows, hover tint).
- **Dropzone:** `.dropzone` (dashed glass, crimson drag-over glow).
- **Feedback:** `.alert-*`, `.toast.success/.error/.warning/.info`,
  `.progress-bar`/`.progress-fill` (+ `.indeterminate`), `.spinner`, `.skeleton`.
- **Empty state:** `.empty-state` (icon + title + guidance + CTA). Used wherever
  AI/analytics has no uploaded data yet — **never** replaced with fake data.
- **Overlays:** `.modal-overlay`/`.modal-panel`, Bootstrap `.dropdown-menu`.

---

## 3. Drama vs. restraint

- **Full dramatic treatment** (hero glow, accent headline, glass, motion):
  landing, auth, onboarding, empty-states, the "Analyze My Business" report.
  Use `.glow-wrap` + `.glow-blob` for the signature crimson glow.
- **Calmer treatment** (same identity, dialed-down glow, accent only on primary
  actions/active states): all working dashboards — tables, forms, analytics.
  The data is the hero; keep glows off data-dense screens.

---

## 4. Motion

Animate only `transform` / `opacity`. Everything degrades gracefully.

- **CSS** (`theme.css`): card/stat entrances, hover micro-interactions, hero
  `glowDrift`, dropdown open, skeleton `shimmer`, indeterminate progress.
- **JS** (`static/js/motion.js`): KPI **count-up** (animates real values 0→N,
  preserving currency/grouping/suffix), **scroll reveal** for `[data-reveal]`
  (manual viewport scan — reliable everywhere), and the Analyze-run progress bar.

### Reduced motion — follows the OS setting only
There is no in-app "Reduce motion" toggle. Motion follows `prefers-reduced-motion`
exclusively:
1. Global CSS safety net: `@media (prefers-reduced-motion: reduce)` disables all
   animation/transition app-wide.
2. `motion.js` checks the same media query and, when the OS setting is on,
   reveals all `[data-reveal]` content instantly (never stuck invisible).

---

## 5. Responsiveness

Mobile-first; verified at 375 / 768 / 1024 / 1440px with no horizontal overflow.
- Side nav → off-canvas drawer below **992px** (`< lg`); hamburger via `d-lg-none`.
- KPI tiles reflow 4 → 2 → 1; `.grid-3/.grid-4/.split-*` collapse; wide tables
  scroll horizontally inside their card.
- Touch targets ≥ 44px (buttons, inputs, nav links).
- Fluid `clamp()` type; the hero glow scales down on small screens.

---

## 6. Theming (two themes)

Two themes switch via `data-theme` on `<html>`: **dark** (default, crimson) and
**light** (indigo). Token names are identical; only values differ.

- **Storage key:** `localStorage['smartserve-theme']` = `'dark'` | `'light'`.
- **Default logic:** saved choice → OS `prefers-color-scheme` → dark fallback.
- **No-FOUC:** a script at the very top of `<head>` (in `base.html` and the
  styleguide) sets `data-theme` before any CSS/paint.
- **Toggle:** a labeled **"Change Theme"** `<button>` (text + moon/sun icon) in the
  sidebar's Settings section (`#themeToggleSidebar`/`#themeIconSidebar`), at every
  screen size, plus a matching button on `/styleguide`. Real button, `aria-label`
  + `aria-pressed`, keyboard-operable, ≥44px touch target. It flips `data-theme`,
  persists the choice, swaps the icon, and calls `applyChartTheme()`.
- **Post-load transition:** `app.js` adds `html.theme-ready` after first paint, so
  switching themes animates (~200ms) but the initial load never flashes a
  transition. Disabled under `prefers-reduced-motion`.
- **JS-driven visuals re-theme on toggle:** Chart.js charts register via
  `SmartServe.registerChart()` (registry initialized in `<head>`) and are recolored
  by `applyChartTheme()` reading tokens through `getComputedStyle`. Film-grain is
  gated to dark; the hero glow softens on light; skeleton shimmer and focus rings
  use theme-scoped tokens; glass panels read `--glass-*` so they flip automatically.

## 7. Accessibility

- Light-mode text and status colors verified **WCAG AA** (see the Text/Status tables).
- Status is never color-only — always paired with an icon + label.
- Visible focus rings in both themes via `--focus-ring`; toggle is keyboard- and
  screen-reader-operable.
- Full `prefers-reduced-motion` support, driven entirely by the OS setting (no
  in-app override).
