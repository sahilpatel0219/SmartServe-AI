# SmartServe AI — Setup Guide

AI-powered Operating System for food businesses (restaurants, cafés, bakeries, cloud kitchens, juice bars, food trucks).

---

## Prerequisites

| Requirement | Minimum version | Notes |
|---|---|---|
| Python | 3.11+ | 3.12 recommended |
| MongoDB | 6.0+ | Local or Atlas |
| pip | Latest | `python -m pip install --upgrade pip` |
| Git | Any | Optional |

---

## 1. Clone / Download

```bash
cd your-projects-folder
# If using git:
git clone <repo-url> SmartServe\ AI
cd SmartServe\ AI
```

---

## 2. Create a Virtual Environment

```bash
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Key packages installed:

| Package | Version | Purpose |
|---|---|---|
| Django | 6.0.5 | Web framework |
| djangorestframework | 3.17.1 | REST API layer |
| djangorestframework-simplejwt | 5.5.1 | JWT auth |
| pymongo | 4.17.0 | MongoDB driver |
| pandas | 2.3.3 | Data wrangling |
| xgboost | 3.2.0 | ML forecasting |
| openpyxl | 3.1.5 | Excel read/write |
| reportlab | 5.0.0 | PDF export |
| python-decouple | 3.8 | `.env` config |

> **Why XGBoost instead of Prophet?**
> Facebook Prophet requires a C++ compiler at install time, which causes frequent build failures on Windows. XGBoost installs as a pre-built wheel on all platforms and provides equivalent (often better) time-series accuracy via lag-feature engineering.

---

## 4. Configure Environment Variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set:

```dotenv
# Django
SECRET_KEY=your-very-long-random-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=smartserve_db

# AI Assistant (optional — leave blank to use stats-based fallback)
# Set LLM_PROVIDER to 'anthropic' or 'openai'
LLM_PROVIDER=
LLM_API_KEY=

# Email (optional — for verification emails)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

> **LLM configuration:**
> - `LLM_PROVIDER=anthropic` + `LLM_API_KEY=sk-ant-...` → uses Claude Haiku 4.5 (fast, cheap)
> - `LLM_PROVIDER=openai` + `LLM_API_KEY=sk-...` → uses GPT-4o-mini
> - Leave both blank → SmartServe uses a built-in stats-based answerer (no API cost, answers from real data)

---

## 5. Start MongoDB

**Local MongoDB:**
```bash
# Windows (if installed as a service)
net start MongoDB

# macOS (Homebrew)
brew services start mongodb-community

# Linux / WSL
sudo systemctl start mongod

# Docker (easiest cross-platform option)
docker run -d --name smartserve-mongo -p 27017:27017 mongo:6
```

**MongoDB Atlas (cloud):**
1. Create a free cluster at [mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Get your connection string (format: `mongodb+srv://user:pass@cluster.mongodb.net/`)
3. Set `MONGO_URI=mongodb+srv://...` in `.env`

---

## 6. Run Database Migrations

SmartServe uses **SQLite** (default) for users/auth and **MongoDB** for all operational data.

```bash
python manage.py migrate
```

To use PostgreSQL instead:
```dotenv
# Add to .env:
DATABASE_URL=postgres://user:pass@localhost:5432/smartserve_db
```
Then `pip install psycopg2-binary` and re-run migrations.

---

## 7. Create a Superuser (Admin Access)

```bash
python manage.py createsuperuser
```

---

## 8. Collect Static Files (Production Only)

```bash
python manage.py collectstatic
```

For development, static files are served automatically by `runserver`.

---

## 9. Start the Development Server

```bash
python manage.py runserver
```

Visit: **http://127.0.0.1:8000**

---

## 10. First Run Walkthrough

1. **Register** → create your account at `/accounts/register/`
2. **Create Business** → name, type (restaurant/café/bakery/etc.), address
3. **Upload Data** → go to Data Import Center (`/onboarding/`) and upload:
   - `sales` — at least 30 rows to unlock AI analysis
   - `inventory` — for stock alerts and waste tracking
   - `menu` — for profitability analysis
   - `orders` — for demand forecasting
4. **Analytics** → `/analytics/` — revenue trends, top items, busiest days
5. **AI Analysis** → `/ml/` — run the AI pipeline to get:
   - 7-day revenue forecast (XGBoost)
   - Menu engineering matrix (Stars / Plowhorses / Puzzles / Dogs)
   - Food waste risk alerts
   - Business health score (0–100)
   - Natural-language AI insights
6. **AI Assistant** → `/assistant/` — ask questions about your data in plain English
7. **Reports** → `/reports/` — export PDF and Excel reports

> **Important:** AI features (forecasts, health score, insights) only work with your uploaded data. No demo or mock data is ever used. Each business's data is fully isolated — multi-tenant by `business_id`.

---

## Architecture Overview

```
SmartServe AI
├── smartserve/          # Project config (settings, urls, wsgi)
├── mongo/               # MongoDB client, collections, repository
│   ├── client.py        # Singleton pymongo connection
│   ├── collections.py   # Named collection accessors
│   └── repository.py    # Generic CRUD with business_id scoping
├── accounts/            # Users, Businesses, Memberships, Subscriptions
├── core/                # Dashboard, landing, context processors
├── onboarding/          # CSV/XLSX upload pipeline, data import center
├── catalog/             # Menu items + recipe mappings
├── inventory/           # Stock management + expiry tracking
├── orders/              # Order lifecycle + inventory auto-deduction
├── customers/           # Customer profiles + segmentation (VIP/Regular/Inactive)
├── staff/               # Employees + attendance
├── suppliers/           # Suppliers + purchase orders
├── ml_engine/           # AI/ML pipeline
│   └── services/
│       ├── pipeline.py       # Orchestrator
│       ├── forecasting.py    # XGBoost 7-day revenue forecast
│       ├── profitability.py  # Menu engineering matrix
│       ├── waste.py          # Food waste risk scoring
│       ├── health_score.py   # 5-component health score (0–100)
│       └── insights.py       # Natural-language insight generation
├── analytics/           # Chart.js dashboards (revenue, top items, DOW heatmap)
├── assistant/           # AI chat panel (pluggable LLM + stats fallback)
├── notifications/       # Smart alerts (low stock, expiry, waste risk)
├── reports/             # PDF (reportlab) + Excel (openpyxl) exports
├── static/
│   ├── css/design-system.css  # Full design token system
│   └── js/app.js              # UI utilities (toast, sidebar, dropzone)
└── templates/           # All HTML templates (base + per-app)
```

**Database split:**
- **SQLite / PostgreSQL** (Django ORM): Users, Businesses, Memberships, Subscriptions, Roles
- **MongoDB** (pymongo): Sales records, Inventory, Menu items, Orders, Customers, Staff, Predictions, Insights, Notifications — everything operational

---

## Uploading Data — Template Format

Download CSV templates from the Data Import Center, or use these column names:

| Upload type | Required columns | Optional columns |
|---|---|---|
| `sales` | date, item_name, quantity, revenue | cost, category, order_type |
| `inventory` | item_name, quantity, unit, cost_per_unit, reorder_level | expiry_date, category, supplier |
| `menu` | item_name, category, price | cost, is_available, description |
| `orders` | order_date, order_id, item_name, quantity, amount | order_type, customer_name, status |

- Date format: `YYYY-MM-DD` (e.g. `2024-01-15`)
- Numeric columns: no currency symbols; commas allowed (e.g. `1,200` is fine)
- Column names are case-insensitive and spaces are normalized to underscores

---

## Docker (Optional)

```bash
docker-compose up --build
```

The `docker-compose.yml` starts:
- `web` — Django on port 8000
- `mongo` — MongoDB on port 27017

For production, replace `DEBUG=True` with `DEBUG=False` and set a strong `SECRET_KEY`.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: pymongo` | Run `pip install -r requirements.txt` inside the venv |
| MongoDB connection refused | Check `mongod` is running; verify `MONGO_URI` in `.env` |
| `SECRET_KEY` error on startup | Copy `.env.example` to `.env` and set a secret key |
| AI analysis fails with "not enough data" | Upload at least 30 sales records first |
| PDF export error (reportlab not found) | Run `pip install reportlab` |
| Static files not loading | Run `python manage.py collectstatic` (production) or check `DEBUG=True` (dev) |
| Upload preview session expires | For files > 5000 rows, records are committed directly — no preview step |

---

## Security Notes

- All secrets live in `.env` — never commit it (it's in `.gitignore`)
- Multi-tenancy: every MongoDB document is scoped by `business_id` — one business can never read another's data
- JWT tokens expire after 60 minutes (access) / 7 days (refresh)
- File uploads are validated server-side before insertion; only CSV and XLSX are accepted

---

*Built with Django 6, MongoDB, XGBoost, Chart.js, Bootstrap 5, and Bootstrap Icons.*
