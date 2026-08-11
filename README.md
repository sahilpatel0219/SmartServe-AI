# SmartServe AI

**An AI-powered Operating System for food businesses.**

Cafés, restaurants, bakeries, cloud kitchens, and food stalls typically run on five or six disconnected tools — POS, inventory, staff scheduling, delivery dashboards, accounting, analytics. SmartServe AI replaces them with one platform, and adds the thing none of them do: **it predicts what the business should buy, cook, staff, and promote — before the problem happens.**

> **Core principle:** every forecast, insight, and recommendation is generated from the business's **own uploaded data**. The system never shows mock, seeded, or demo predictions. If there's no data, it says so and asks for an upload.

---

## ⚠️ Project Status

This project is **in active development**. This README documents the intended system; the table below is the source of truth for what is actually working.

**Keep this table updated as you build. It is the honest answer to "what's done?"**

| Module | Status |
|---|---|
| Authentication & role-based access | 🟡 In progress |
| Business registration / workspace | 🟡 In progress |
| Data upload + validation (CSV/Excel) | 🟡 In progress |
| Menu & recipe mapping | ⚪ Planned |
| Smart inventory + auto-deduction | ⚪ Planned |
| Order management | ⚪ Planned |
| Sales & profit analytics | ⚪ Planned |
| AI demand forecasting | ⚪ Planned |
| Food waste prediction | ⚪ Planned |
| Business health score | ⚪ Planned |
| Forecast accuracy evaluation | ⚪ Planned |
| QR ordering | ⚪ Planned |
| Reports (PDF / Excel) | ⚪ Planned |
| AI assistant (chat) | 🔵 Stubbed |
| Delivery integrations (Zomato / Swiggy) | 🔵 Stubbed |
| Payments | 🔵 Stubbed |
| Multi-branch support | 🔵 Stubbed |

**Legend:** ✅ Working · 🟡 In progress · ⚪ Planned · 🔵 Stubbed (interface exists, not functional)

---

## Features

### Core

- **Data Upload & Validation** — Import sales history, inventory, menu, and past orders via CSV or Excel. Files are validated column-by-column with a row-level error report and a preview before anything is committed. Downloadable templates are provided for each upload type.
- **Smart Inventory** — Ingredients are mapped to menu items via recipes, so stock auto-deducts when an item sells. Low-stock and expiry alerts fire against configurable thresholds.
- **AI Demand Forecasting** — Time-series forecasting on the business's own sales history to predict next-day, weekend, and per-item demand.
- **Food Waste Prediction** — Cross-references stock, expiry dates, and sales velocity to flag inventory likely to expire before it sells, with an estimated cost.
- **Profit Analytics** — Per-item revenue, cost, and margin. Classifies the menu into Stars / Puzzles / Dogs to guide pricing and menu decisions.
- **Business Health Score** — A single 0–100 score derived from revenue growth, profit margin, food waste, customer retention, and inventory efficiency, with a full breakdown of how it was calculated.
- **Unified Operations** — Orders (counter, QR, delivery), staff and attendance, customers, and suppliers in one dashboard.
- **Reports** — Sales, inventory, and profit reports exportable to PDF and Excel.

### Analyze My Business

A single action that runs the full pipeline on the uploaded data — sales forecast, demand forecast, inventory forecast, profit analysis, waste risk, health score, insights, and recommendations — and returns one decision-support report.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11+, Django 6.x, Django REST Framework (JSON API only) |
| **Auth** | JWT via `djangorestframework-simplejwt`; CORS via `django-cors-headers` |
| **Database** | MongoDB (business data, uploads, predictions) + relational DB (auth, users, roles) |
| **Frontend** | React 18 + Vite, React Router, TanStack Query, Axios, Recharts |
| **AI / ML** | Pandas, NumPy, scikit-learn, XGBoost |
| **Deployment** | Docker, Nginx, Gunicorn, AWS / DigitalOcean |

**On the hybrid database:** Django's auth and admin are built on the ORM, so users, roles, and subscriptions live in a relational DB. High-volume, schema-flexible data (uploaded datasets, sales records, orders, predictions) lives in MongoDB behind a repository layer. Views never touch `pymongo` directly.

---

## Design System

- **Layout:** Bento-grid-led — modular rounded cells on overview and analytics screens; conventional tables, forms, and kanban layouts where they serve the content better.
- **Themes:** Dark (deep-red brand) is the default; a light theme (green brand) is available via the "Change Theme" control in the nav. Both are driven entirely by CSS custom properties under `[data-theme]` scopes.
- **Typography:** Helvetica / Helvetica Neue / Arial sans-serif system, with a fluid `clamp()` scale and tabular numerals on all data.
- **Motion:** Restrained — staggered entrance, scroll reveal, hover lift, count-up numbers. Honors `prefers-reduced-motion` automatically.
- **Status colors** are deliberately kept separate from the brand color so alerts remain readable in both themes.

The design system now lives in **`frontend/src/styles/theme.css`** as the React
app's global stylesheet — same token names, same two `[data-theme]` scopes as the
original Django stylesheet, so both themes render identically. Reusable
components are in `frontend/src/components/` (`ui.jsx` for cards, bento cells,
KPI tiles, tables, modals, forms, empty states; `charts.jsx` for Recharts
wrappers that re-read theme colors on toggle; `AppShell.jsx` for the side nav and
top bar).

See `STYLEGUIDE.md` for the component library reference.

---

## Getting Started

### Prerequisites

- Python 3.11+
- MongoDB (local install or a hosted cluster such as MongoDB Atlas)
- pip / virtualenv

- Node.js 18+ (for the React frontend)

### Architecture

The app runs as **two processes**: a Django REST API that returns JSON only, and a
React single-page app that owns the entire UI. They talk over HTTP and are
connected by exactly two settings — the frontend's `VITE_API_URL` and the
backend's `CORS_ALLOWED_ORIGINS`.

```
frontend/  React + Vite SPA  ──HTTP + JWT──▶  Django REST API (/api/*)
  :5173                                          :8000
```

Every endpoint is documented in **[`API.md`](API.md)** — method, URL, request
body, and response shape.

### Installation — backend

```bash
# 1. Clone
git clone <TODO: repo URL>
cd smartserve-ai

# 2. Virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Dependencies
pip install -r requirements.txt

# 4. Environment variables
cp .env.example .env
# Open .env and fill in your values — see SETUP.md.
# CORS_ALLOWED_ORIGINS must include wherever Vite serves the frontend.

# 5. Database
python manage.py migrate

# 6. Create an admin account
python manage.py createsuperuser
```

### Installation — frontend

```bash
cd frontend
npm install
cp .env.example .env      # VITE_API_URL should point at the backend's /api
```

### Running both (two terminals)

Terminal 1 — API:

```bash
python manage.py runserver
```

Terminal 2 — React app:

```bash
npm run dev --prefix frontend
```

Then open **http://localhost:5173**. The Django admin stays at
http://127.0.0.1:8000/admin, and the API root is http://127.0.0.1:8000/api/.

### How the two are wired together

| Setting | Where | Purpose |
|---|---|---|
| `VITE_API_URL` | `frontend/.env` | Base URL the React app calls. Default `http://127.0.0.1:8000/api` |
| `CORS_ALLOWED_ORIGINS` | `.env` (backend) | Origins allowed to call the API. Must include `http://localhost:5173` |

If you change the Vite port or serve the API from another host, update **both**
or the browser will block the requests.

### Docker

```bash
docker-compose up --build
```

This starts the web service and MongoDB together.

---

## Configuration

All configuration is via environment variables — **never commit `.env`**. See **`SETUP.md`** for the full checklist of what you must change before running or deploying, including:

- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
- `MONGO_URI`, `MONGO_DB_NAME` (and how to switch from local Mongo to Atlas)
- Relational database settings (SQLite in dev → PostgreSQL in production)
- Email / SMTP credentials
- `LLM_PROVIDER`, `LLM_API_KEY` (optional — for the AI assistant)
- Which features are stubbed and what must be plugged in to make them live

---

## Deployment

The frontend and backend deploy to **two separate hosts** — this isn't optional.
Vercel is a static/serverless host built for frontends; it doesn't suit a
Django app with MongoDB connections and heavy ML dependencies (XGBoost,
scikit-learn, pandas) well. The working split:

| Part | Host | Why |
|---|---|---|
| `frontend/` (React) | **Vercel** | Purpose-built for this — fast, free, zero config |
| Everything else (Django API) | **Render** (or Railway/Fly.io/a VPS) | Handles a long-running Python process, real dependency sizes, and persistent DB connections normally |
| MongoDB | **Atlas** (unchanged) | Already cloud-hosted; nothing to migrate |

### Backend → Render

1. Push this repo to GitHub.
2. Render dashboard → **New → Blueprint** → point at the repo. It reads
   [`render.yaml`](render.yaml) and provisions a web service + a free Postgres
   database (for accounts/roles — SQLite has no persistent disk on Render's
   free tier, so Postgres replaces it in production; MongoDB keeps holding all
   the operational business data, unchanged).
3. In the service's **Environment** tab, fill in the values `render.yaml`
   deliberately leaves blank (`sync: false`):
   - `MONGO_URI` — your Atlas connection string
   - `CORS_ALLOWED_ORIGINS` — your Vercel URL, e.g. `https://smartserve-ai.vercel.app`
   - `CSRF_TRUSTED_ORIGINS` — same Vercel URL (only needed for `/admin/`)
   - `LLM_API_KEY` — optional
4. Deploy. Render runs `collectstatic` + `migrate` automatically (see
   `buildCommand` in `render.yaml`), then starts Gunicorn.
5. **Whitelist Render's outbound traffic in Atlas** — Network Access → Add IP
   → `0.0.0.0/0` is simplest for a PaaS host with rotating egress IPs (Render
   doesn't publish a static IP range on the free tier).

No `render.yaml`? Use the plain [`Procfile`](Procfile) instead — same two
commands (`release: migrate`, `web: gunicorn ...`), works on Railway/Heroku-style
hosts too.

### Frontend → Vercel

1. Vercel dashboard → **New Project** → import the repo → set **Root
   Directory** to `frontend/` (this is a monorepo; Vercel needs to know the
   frontend isn't at the repo root).
2. Framework preset: Vite (auto-detected). Build command / output directory:
   defaults are correct (`npm run build` / `dist`).
3. **Settings → Environment Variables** → add `VITE_API_URL` =
   `https://<your-render-service>.onrender.com/api` — **not** in a `.env`
   file; Vercel doesn't read repo `.env` files, only its own dashboard vars.
4. Deploy. [`frontend/vercel.json`](frontend/vercel.json) rewrites all paths
   to `index.html` so React Router's client-side routes (e.g. a direct visit
   to `/dashboard`) don't 404 on Vercel's static host.
5. Go back to Render and set `CORS_ALLOWED_ORIGINS` to the real Vercel URL
   Vercel just gave you (steps 3 above referenced it in advance — close the
   loop once both sides exist).

### After both are live

Register an account at your Vercel URL — it calls the Render API, which reads
from Atlas. Same app, same behavior as local dev, just deployed.

---

## Sample Data

Sample CSV files for a fictional café (**Cafe LJ**) are included so the upload and analysis flow can be tested immediately:

| File | Contents |
|---|---|
| `cafe_lj_menu.csv` | 18 menu items with prices and categories |
| `cafe_lj_inventory.csv` | 21 ingredients with stock, cost, expiry, thresholds |
| `cafe_lj_sales.csv` | 130 days of daily sales (enough history for forecasting) |
| `cafe_lj_orders.csv` | ~1,200 individual orders over 30 days |

> These are **synthetic** — realistic in shape, but not real business data. They exist for testing, not for benchmarking model accuracy.

**Minimum data required before AI features activate:** roughly 30+ days of clean sales history. Below that, the system will tell the user rather than produce an unreliable forecast.

---

## Project Structure

```
smartserve/       # project config
api/              # REST API: serializers, JWT auth, tenancy, per-domain views
frontend/         # React + Vite SPA (the entire UI)
core/             # shared utils, legacy templates (being retired)
accounts/         # auth, roles, workspaces, subscriptions
onboarding/       # business registration + data upload + validation
catalog/          # menu items, categories, recipes
inventory/        # stock, expiry, alerts, auto-deduction
orders/           # orders, statuses, live board
customers/        # customer profiles + segmentation
staff/            # employees, shifts, attendance
suppliers/        # suppliers + purchase orders
analytics/        # dashboards, KPIs, trends
ml_engine/        # forecasting, waste, profit, health score
assistant/        # AI assistant + recommendations
reports/          # PDF / Excel generation
notifications/    # alerts
mongo/            # pymongo client + data-access layer
```

---

## Known Limitations

Stated honestly, because they shape how the system should be judged:

- **Forecast quality depends on data quality.** Real uploaded data is messy — inconsistent item names, missing dates, refunds as negative rows. Automated cleaning on upload is a priority, not a solved problem.
- **Accuracy is not yet measured.** A forecast without an error metric is a claim, not a result. A predicted-vs-actual accuracy dashboard (MAE / MAPE) is the next high-priority item.
- **Multi-tenant isolation needs explicit testing.** Workspaces are scoped by `business_id`; this must be verified with tests, not assumed.
- **Several features are stubbed** — payments, delivery-platform integrations, and the LLM-backed assistant require external API keys and access that are not wired up.
- **v1 is single-branch.** Multi-branch support for chains is deferred.

---

## Roadmap

- [ ] Automated data cleaning and fuzzy item-name matching on upload
- [ ] Forecast accuracy dashboard (predicted vs actual, MAE / MAPE, confidence intervals)
- [ ] Reorder-point logic accounting for supplier lead time and a safety buffer
- [ ] Audit log wired through all destructive and financial actions
- [ ] Multi-tenant isolation test suite
- [ ] POS / Google Sheets sync
- [ ] Multi-branch support

---

## Team

| Name | Role | Ownership |
|---|---|---|
| `Patel Sahil` | Backend Engineer | Django, MongoDB, auth, multi-tenant isolation, inventory logic |
| `Patel Maahi` | AI/ML Engineer | Data pipeline, forecasting models, accuracy evaluation |
| `Mewada Het` | Frontend Engineer | UI/UX, bento design system, dashboards, upload flow |

All members contribute to integration, testing, and documentation.

---

## Screenshots

`TODO: add once the UI is built — dashboard, upload flow, Analyze My Business report, both themes.`

---

## License

`TODO: choose a license (MIT is a reasonable default) or state that this is a private academic project.`

---

## Acknowledgements

Built as a `TODO: final-year / academic / personal` project. Portions of the codebase were scaffolded with AI assistance; architecture, data modeling, and model evaluation decisions are our own.
