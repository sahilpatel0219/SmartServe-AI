# SmartServe AI — Design System ("Noir Crimson")

A dark, premium, editorial UI: near-black canvas, a single glowing crimson
accent, tight grotesk headlines, glassmorphic depth, and tasteful motion.

> **Live reference:** run the app and open **`/styleguide`** to see every
> component and state rendered in the real theme.
>
> **Single source of truth:** [`static/css/theme.css`](static/css/theme.css).
> All color, spacing, radius, shadow, blur, and type are CSS custom properties.
> No component hardcodes a hex value outside that file.

---

## 1. Tokens

### Surfaces
| Token | Value | Use |
|---|---|---|
| `--bg-deep` | `#070708` | Behind hero/auth, deepest layer |
| `--bg-base` | `#0A0A0B` | App background |
| `--bg-elev-1` | `#141416` | Cards, panels, sidebar |
| `--bg-elev-2` | `#1A1A1D` | Inputs, table headers, footers |
| `--glass-bg` | `rgba(255,255,255,.04)` | Glassmorphic raised/overlay surfaces |
| `--glass-border` | `rgba(255,255,255,.09)` | Glass borders |
| `--hairline` | `rgba(255,255,255,.08)` | Hairline dividers/borders |

### Text
| Token | Value | Use |
|---|---|---|
| `--text-primary` | `#F4F4F3` | Body & headings |
| `--text-muted` | `#A1A1AA` | Secondary text |
| `--text-faint` | `#6B6B73` | Captions, placeholders, icons |

### Brand & status
The brand is red, so red is **not** the generic error color. Use `--brand` for
interactive chrome (buttons, links, active nav, highlights) and solid *critical*
banners. Use the **status palette** for data states, deltas, stock levels, and
validation. Brand vs. alert is distinguished by **fill + icon + position**, not
hue alone.

| Token | Value | Use |
|---|---|---|
| `--brand` | `#E5392E` | CTAs, links, active states, highlights |
| `--brand-hover` | `#C72A22` | Hover |
| `--brand-tint` / `--brand-glow` | crimson @ .12 / .45 | Soft fills / glow |
| `--success` | `#34D399` | Positive data, "in stock", up-deltas |
| `--warning` | `#FBBF24` | Caution, "low" |
| `--info` | `#60A5FA` | Neutral/secondary data series |
| `--danger` | `#FF5A52` | Negative data (losses, below-threshold) |
| `--critical` | = `--brand` | Solid system-critical banners only |

Each status color has a matching `*-tint` for soft badge/alert backgrounds.

### Radius, blur, elevation
`--r-sm 10px` · `--r-md 14px` · `--r-lg 20px` · `--r-pill 999px` · `--blur 20px`
`--shadow-1` (resting) · `--shadow-2` (raised) · `--shadow-glow` (crimson) ·
`--inset-hi` (1px top light-catch on cards).

### Type
- **Display:** `Inter Tight` (600/700/800) — headlines, KPI numbers, titles.
- **Body:** `Inter` (400/500/600).
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
- **Buttons:** `.btn` + `.btn-primary` (crimson, glow on hover) /
  `.btn-secondary` (glass) / `.btn-outline` / `.btn-ghost` / `.btn-danger`;
  sizes `.btn-sm/.btn-lg`, `.btn-pill`.
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

### Reduced motion (three layers)
1. Global CSS safety net: `@media (prefers-reduced-motion: reduce)` disables all
   animation/transition.
2. User opt-out: the sidebar **"Reduce motion"** toggle sets `html.no-motion`
   (persisted in `localStorage` as `ss_motion`), which disables CSS motion.
3. `motion.js` checks both and, when motion is off, reveals all `[data-reveal]`
   content instantly (never stuck invisible).

---

## 5. Responsiveness

Mobile-first; verified at 375 / 768 / 1024 / 1440px with no horizontal overflow.
- Side nav → off-canvas drawer below **992px** (`< lg`); hamburger via `d-lg-none`.
- KPI tiles reflow 4 → 2 → 1; `.grid-3/.grid-4/.split-*` collapse; wide tables
  scroll horizontally inside their card.
- Touch targets ≥ 44px (buttons, inputs, nav links).
- Fluid `clamp()` type; the hero glow scales down on small screens.

---

## 6. Theming

Dark is the **default and only built theme**. Tokens are structured so a light
theme could be added later under a `[data-theme="light"]` block, but it is
intentionally not built now. The pre-paint script in `base.html` applies the
theme before first paint to avoid flash.
