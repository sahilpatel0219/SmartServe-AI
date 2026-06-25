# SmartServe AI — Claude Code Build Prompt

> **How to use this file:** Open Claude Code in an empty project folder and paste everything below the line marked `=== PROMPT START ===`. You can delete this top section first. If your machine is missing tools (Python, MongoDB, etc.), let Claude Code install/scaffold them as part of Phase 0.

---

=== PROMPT START ===

You are my senior full-stack engineer. Build a real, production-quality product called **SmartServe AI** — an AI-powered Operating System for food businesses (restaurants, cafés, bakeries, food stalls, cloud kitchens, juice bars, food trucks). This is NOT a throwaway CRUD app; it must look and behave like a startup product a real owner would pay for.

Work in **phases**. After each phase, ensure the app actually **runs** (`python manage.py runserver`) with no errors before moving on. Commit after each phase with a clear message. Ask me nothing unless you hit a true blocker — make sensible professional decisions and document them.

---

## 0. NON-NEGOTIABLE RULES (read first, apply everywhere)

1. **AI predictions, forecasts, insights, and health scores must ONLY work after the user has uploaded their own business data.** There must be NO mock, seeded, hardcoded, or demo prediction data anywhere. If no data is uploaded, every AI/analytics screen shows a clean empty-state that invites the user to upload data — never fake numbers.
2. Every ML model is trained/run on **that specific business's uploaded data only**. Multi-tenant isolation: one business can never see another's data.
3. No secrets in code. Every key, password, or external endpoint goes in a `.env` file loaded via `python-decouple` or `django-environ`, with a matching `.env.example` containing placeholders.
4. Code must be clean, commented where non-obvious, and organized into reusable Django apps.
5. At the very end you MUST produce a `SETUP.md` that lists, in plain language, exactly what I have to change to run and deploy this (see Section 9).

---

## 1. TECH STACK (use exactly this — do not substitute)

- **Backend:** Python 3.11+, Django 5.x, Django REST Framework
- **Database (hybrid — important):**
  - Relational DB (SQLite for dev, Postgres-ready for prod) for Django's built-in **auth, users, roles, subscriptions, sessions** — because Django auth/admin needs the ORM.
  - **MongoDB** (via `pymongo` + a thin data-access layer) for high-volume / flexible data: **uploaded datasets, sales records, orders, predictions, generated insights, notifications, logs.**
  - Do NOT try to force Django's auth onto MongoDB. Keep the split clean and document it.
- **Frontend:** Django templates + HTML5 + CSS3 + **Bootstrap 5** + vanilla JavaScript + **Chart.js** for charts. No React.
- **ML / Data:** Pandas, NumPy, scikit-learn, XGBoost, Prophet (or statsmodels if Prophet install is painful — pick whichever installs cleanly and note it).
- **File handling:** `openpyxl` + Pandas for `.xlsx`/`.csv` parsing and validation.
- **Auth:** Django sessions for the web app + DRF token/JWT (`djangorestframework-simplejwt`) for any API endpoints.
- **Background/heavy ML:** run synchronously for the MVP, but isolate ML in a service layer so it can later move to Celery + Redis. Note this in SETUP.md.
- **Deployment-ready:** include a `Dockerfile`, `docker-compose.yml` (web + mongo), `requirements.txt`, and gunicorn config. Don't deploy — just make it ready.

---

## 2. DESIGN SYSTEM (this defines the whole look — follow precisely)

The aesthetic is **"Minimal + Spatial UI"**: content-first minimalism with a clear sense of depth, layering, and floating surfaces. It must feel calm, premium, and professional — like a modern analytics SaaS.

**Spatial UI rules:**
- Floating cards on a soft canvas, generous whitespace, clear foreground/background separation.
- Soft, layered, multi-step shadows (not one harsh drop shadow) to create depth, e.g. `0 1px 2px rgba(16,24,40,.04), 0 8px 24px rgba(16,24,40,.06)`.
- Rounded corners: 12–16px on cards, 8–10px on inputs/buttons.
- Subtle **glassmorphism** (backdrop-blur, semi-transparent white) on the top nav, modals, and sticky overlays only — used sparingly.
- Gentle gradients and subtle borders (hairline `1px` borders in a near-canvas tone) for layering, not decoration.
- Smooth micro-interactions: 150–200ms ease transitions on hover/focus, subtle lift on card hover.

**Minimalism rules:**
- Restrained palette, lots of breathing room, strong typographic hierarchy, no visual clutter, no gradients-for-gradients'-sake.

**Color palette (recommended — "Fresh Professional"):**
- Ink / primary text: `#16181D`
- Muted text: `#6B7280`
- Canvas (page bg): `#F6F6F4` (warm paper)
- Surface (cards): `#FFFFFF`
- Hairline border: `#E7E7E3`
- Primary accent (growth/profit/fresh): `#2D6A4F` (deep professional green), hover `#245A42`
- Secondary accent (food/energy/appetite): `#E8A33D` (warm amber)
- Success `#2D6A4F`, Warning `#E8A33D`, Danger `#DC2626`, Info `#2563EB`
- Use the accents sparingly — neutrals dominate; color signals meaning (money, alerts, status).

Implement the palette and all spacing/radius/shadow as **CSS custom properties** (`:root` variables) so it's themeable. Provide a subtle dark-mode-ready structure but ship light mode.

**Typography:** Use **Inter** (or Plus Jakarta Sans) for UI, loaded from Google Fonts; use `tabular-nums` for all numbers in tables/metrics. Clear scale: page title, section title, card title, body, caption.

**Iconography:** use a clean open-source icon set (Lucide via CDN, or Bootstrap Icons). Consistent stroke weight only.

Build a small **reusable component library** in templates/partials + CSS: stat card (KPI tile), data table, chart card, empty-state block, upload dropzone, badge/status pill, modal, toast/notification, side nav, top bar. Every page composes these — do not hand-roll one-off styles.

---

## 3. ARCHITECTURE & FOLDER STRUCTURE

Create a clean Django project with separate apps:

```
smartserve/                 # project config
core/                       # base templates, design system, shared utils, empty-states
accounts/                   # auth, roles, business workspace, subscriptions
onboarding/                 # business registration + data upload + validation  <-- critical
catalog/                    # menu items, categories, ingredients/recipes
inventory/                  # stock, units, expiry, alerts, auto-deduction
orders/                     # orders + statuses + live tracking
customers/                  # customer profiles + segmentation
staff/                      # employees, shifts, attendance
suppliers/                  # suppliers + purchase orders
analytics/                  # dashboards, KPIs, sales trends (REAL data only)
ml_engine/                  # forecasting, waste, profit, health score (gated on upload)
assistant/                  # AI restaurant assistant (chat) + recommendations
reports/                    # PDF/Excel report generation
notifications/              # smart alerts
mongo/                      # pymongo client, collection accessors, data-access layer
```

Keep all ML logic inside `ml_engine/services/` as plain functions/classes (no view logic). Keep Mongo access behind a repository layer in `mongo/` — views never touch pymongo directly.

---

## 4. USER ROLES & MULTI-TENANCY

- **Super Admin:** manages all businesses, subscriptions, platform-wide analytics.
- **Business Owner:** full control of their own workspace (one workspace = one business).
- **Manager:** orders, staff, reports for their business.
- **Staff:** view shifts, mark attendance, update order status.

Every business is an isolated **workspace**. All data (relational + Mongo) is scoped by `business_id`. Enforce role-based access with Django permissions + DRF permission classes. A user only ever sees their own workspace's data.

---

## 5. DATA MODEL

**Relational (Django ORM):** `User`, `Business` (name, type[Restaurant/Cafe/Bakery/FoodStall/CloudKitchen/JuiceBar/FastFood/FoodTruck], address, contact, GST, logo, opening hours), `Membership` (user↔business↔role), `SubscriptionPlan` (Basic ₹2,999 / Pro ₹7,999 / Enterprise ₹20,000+), `BusinessSubscription`.

**MongoDB collections** (all carry `business_id`): `uploaded_datasets`, `sales_records`, `menu_items`, `ingredients`, `inventory`, `orders`, `customers`, `employees`, `attendance`, `suppliers`, `purchase_orders`, `predictions`, `insights`, `recommendations`, `notifications`, `reports`, `audit_logs`.

---

## 6. MODULES & FEATURES (build all)

**Onboarding & Data Upload (Module priority #1 — this unlocks the AI):**
- Business registration wizard → creates an isolated workspace.
- **Data Import center** supporting **CSV and Excel (.xlsx)** for: Sales history, Inventory, Menu, Historical orders.
- **Validate every upload**: detect required columns, data types, date formats, duplicates; show a clear preview table and a row-level error report before committing. Reject bad files gracefully.
- Provide downloadable **template files** for each upload type so the user knows the expected format.
- Show an **onboarding progress / data-readiness meter** ("Sales ✓, Inventory ✓, Menu ✗") that gates AI features.

**Auth:** registration, login, logout, password reset, email verification (use console email backend in dev), role-based access, login history.

**Restaurant/Business Profile:** name, logo, type, GST, address, contact, hours; QR code generation for the digital menu.

**Menu Management:** categories, items, prices, and **ingredient/recipe mapping** (this drives auto inventory deduction).

**Smart Inventory:** stock, unit, cost, expiry; low-stock & expiry alerts with thresholds; **auto-deduction** of ingredients when an order is placed (based on recipe mapping).

**Order Management:** orders from counter / QR / delivery / phone; statuses Pending→Preparing→Ready→Delivered; live order board.

**Customer Management:** profiles, visit count, spend history; **segmentation** (VIP / Regular / Inactive) computed from real data only.

**Staff Management:** employees, roles, salary, shifts, attendance, leave.

**QR Ordering:** generate QR → opens digital menu → place order / call waiter (payment can be a stubbed flow documented in SETUP.md).

**Suppliers:** supplier details, products, purchase orders, costs.

**Sales Dashboard (analytics, REAL data only):** daily/weekly/monthly sales, revenue/expense/profit, top items, busiest days/hours — all Chart.js, all from uploaded/real data. Empty-state when no data.

**Reports:** sales / inventory / profit reports, export to **PDF and Excel**.

**Notifications:** low stock, expiry approaching, high demand predicted, staff shortage.

**Home Dashboard (ERP-style KPIs):** Today's Revenue, Orders Today, Profit Today, Inventory Alerts, Food Waste, Forecasted Sales — each KPI shows real value OR an empty-state if data is missing.

---

## 7. AI / ML ENGINE (`ml_engine/`) — GATED ON UPLOADED DATA

Each capability must check: "does this business have enough uploaded data?" If not, return a structured `needs_data` response and the UI shows an upload prompt — never a fabricated number.

1. **Sales / Demand Forecasting:** train on the business's historical sales (date, item, qty, revenue). Use Prophet/XGBoost for time-series; produce next-day, weekend, and per-item demand forecasts with a confidence indicator. State minimum data needed (e.g. ≥30 days) and enforce it.
2. **Inventory Forecasting:** combine demand forecast + recipe mapping + current stock → "ingredient X runs out in N days / reorder N units."
3. **Profitability Analytics:** per-item revenue, cost, margin; classify items (Stars / Puzzles / Dogs); pricing & menu recommendations.
4. **Food Waste Prediction:** from inventory + expiry + sales velocity → "N kg of X may expire in M days," with estimated ₹ loss.
5. **Business Health Score (0–100):** composite of revenue growth, profit margin, food waste, customer retention, inventory efficiency — computed only from real data, with a breakdown of how the score was derived.
6. **AI Insights:** auto-generated natural-language insights from the data ("Saturdays generate 32% more revenue," "Cold coffee up 15%"). Generate these from actual computed stats, not templates with random numbers.
7. **AI Recommendations engine:** menu, pricing, and promotion suggestions derived from the analytics above.

**"Analyze My Business" button:** one action that runs forecasting + demand + inventory + profit + waste + health score + insights + recommendations on the uploaded data and renders a single decision-support report. This is the showcase feature — make it polished.

**AI Restaurant Assistant (`assistant/`):** a chat panel where the owner asks questions ("Why were sales low yesterday?", "What should I reorder this weekend?"). Implement it to answer from the business's computed analytics. Make the LLM provider **pluggable via env var** (`LLM_PROVIDER`, `LLM_API_KEY`) so I can wire in an API later; if no key is set, fall back to a rules/stats-based answerer that uses the real computed metrics. Clearly document this in SETUP.md.

---

## 8. ADVANCED / NICE-TO-HAVE (implement if phase budget allows, else stub cleanly and note in SETUP.md)

Dynamic pricing suggestions, customer loyalty/points/coupons, multi-branch support for chains, delivery-platform (Zomato/Swiggy) integration placeholders, Google Sheets sync placeholder.

---

## 9. REQUIRED FINAL DELIVERABLES

1. A working app that runs locally with documented commands.
2. `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `.env.example`.
3. **`README.md`:** what the project is, architecture overview, how to run.
4. **`SETUP.md` — a configuration checklist I must complete.** This is mandatory and must explicitly list, in plain language, every external/changeable thing, including at minimum:
   - All environment variables and what each does (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, relational DB settings, `MONGO_URI` / `MONGO_DB_NAME`, email/SMTP creds, `LLM_PROVIDER` + `LLM_API_KEY` for the AI assistant, any payment keys, any storage/S3 keys).
   - **Where to put my MongoDB connection string** and how to switch from local Mongo to a hosted cluster (e.g. Atlas).
   - **How to create the Super Admin** account (`createsuperuser`) and where the admin server/panel lives.
   - Which features are **stubbed** (payments, delivery integrations, LLM) and exactly what I need to plug in to make them live.
   - How to switch dev → prod (DEBUG off, switch SQLite→Postgres, set ALLOWED_HOSTS, run with gunicorn/Docker).
   - Any Prophet/XGBoost install caveats and the fallback you chose.
   - The minimum data a user must upload before each AI feature activates.

---

## 10. BUILD PHASES (do in this order; app must run after each)

- **Phase 0:** Project scaffold, settings (env-driven), hybrid DB wiring (relational + Mongo client), base templates, full **design system** + reusable components, accounts/auth + roles.
- **Phase 1:** Business registration → workspace, then the **data upload + validation + templates** module. (Nothing AI yet — but the upload pipeline must be solid.)
- **Phase 2:** Core CRUD modules: profile, menu (+recipes), inventory (+auto-deduction), orders, customers, staff, suppliers, QR ordering.
- **Phase 3:** Analytics dashboards + KPIs + reports (PDF/Excel) — strictly real/uploaded data, with empty-states.
- **Phase 4:** `ml_engine` — forecasting, inventory forecast, profit analytics, waste prediction, health score, insights — all **gated on uploaded data**, plus the "Analyze My Business" report.
- **Phase 5:** AI assistant (pluggable LLM + stats fallback), recommendations, smart notifications, advanced/loyalty/multi-branch (stub where needed).
- **Phase 6:** Polish pass (design consistency, empty-states, responsiveness, accessibility), `README.md`, and the mandatory `SETUP.md`.

Begin with Phase 0 now. Keep me updated at the end of each phase with a short summary of what was built and confirm the app runs.

=== PROMPT END ===
