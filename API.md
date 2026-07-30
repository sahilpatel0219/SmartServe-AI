# SmartServe AI — REST API Reference

All endpoints are prefixed with `/api/`. The React app is the only consumer.

## Conventions

**Authentication** — JWT bearer tokens (`djangorestframework-simplejwt`).
Send `Authorization: Bearer <access_token>` on every request except
`auth/register/`, `auth/login/`, and `auth/refresh/`.

**Tenancy** — every business-scoped endpoint resolves the active business from:

1. `X-Business-Id` request header, else
2. `?business_id=` query param, else
3. the user's first active `Membership`.

The resolved id is always re-validated against a real, active `Membership` row,
so a client cannot read or write another business's data by changing the header.
Endpoints return `403` if the user has no active business workspace.

**Roles** — `owner`, `manager`, `staff`. `membership.is_manager` means owner or
manager. Role checks are enforced server-side; the React app only uses the role
to hide controls, never to grant access.

**Errors** — `{"error": "message"}` with an appropriate 4xx/5xx status, or DRF's
standard field-error object (`{"field": ["message"]}`) for serializer validation.

**Mongo ids** — documents are returned with their ObjectId stringified as `id`
(the raw `_id` key is removed).

---

## Auth

### `POST /api/auth/register/`
Public. Creates a user and returns tokens immediately.

Request: `{email, first_name, last_name, phone?, password}` (password min 8 chars)
Response `201`: `{user: {id, email, first_name, last_name, phone, is_email_verified}, access, refresh}`

### `POST /api/auth/login/`
Public.

Request: `{email, password}`
Response `200`: `{access, refresh, user: {...}}`
Also writes a `LoginHistory` row (ip, user agent), matching the old session login.

### `POST /api/auth/refresh/`
Request: `{refresh}` → Response: `{access}`

### `POST /api/auth/verify/`
Request: `{token}` → `200` if valid, `401` otherwise.

### `GET /api/auth/me/`
Response: `{user, active_membership, memberships[]}`
Each membership: `{id, business: {...}, role, is_active, joined_at}`.
This is the endpoint that replaces the old `global_context` template processor.

### `PATCH /api/auth/me/`
Request (any subset): `{first_name, last_name, phone, email}`
Changing `email` also syncs `username`. Rejects an email already used by another account.
Response: updated user.

### `GET /api/auth/login-history/`
Response: last 10 `{ip_address, user_agent, logged_in_at, success}`.

---

## Businesses & onboarding

### `GET /api/businesses/`
Response: the caller's memberships (each with its nested business).

### `POST /api/businesses/`
Creates a business, makes the caller `owner`, attaches a trial `basic` subscription.

Request: `{name, business_type, address?, city?, state?, pincode?, phone?, email?, website?, gst_number?, currency?}`
`business_type` ∈ `restaurant | cafe | bakery | food_stall | cloud_kitchen | juice_bar | fast_food | food_truck`
Response `201`: the business, including `mongo_id` (the `business_id` used in all Mongo docs).

### `GET /api/businesses/<business_id>/`
Response: the business. `404` if the caller has no active membership for it.

### `PATCH /api/businesses/<business_id>/`
**Manager/owner only** (`403` for staff). Request: any writable business field.

### `POST /api/businesses/<business_id>/activate/`
Validates membership and echoes it back. Kept for parity with the old session
`switch_business_view`; the client should store the id and send it as
`X-Business-Id` afterwards (a stateless JWT API has no session to update).

---

## Dashboard

### `GET /api/dashboard/`
Response:
```json
{
  "business": {"id": 1, "name": "Cafe LJ"},
  "mongo_ok": true,
  "kpis": {
    "today_revenue": null, "today_orders": null, "today_profit": null,
    "inventory_alerts": null, "food_waste": null, "forecasted_sales": null,
    "health_score": null, "active_customers": null
  },
  "kpi_date": "2024-05-10",
  "data_readiness": {"score": 40, "items": [{"label": "Sales Data", "done": true}]},
  "latest_insights": [{"_id": "...", "text": "..."}]
}
```
**Every KPI is `null` until real data exists** — the frontend must render an
upload prompt rather than a zero or a placeholder. `kpi_date` is the most recent
date present in the sales data, not today's calendar date (uploaded data is
historical). AI KPIs (`food_waste`, `forecasted_sales`, `health_score`) stay
`null` until an ML analysis run has completed.

---

## Data upload

### `GET /api/uploads/`
Response: `{upload_types[], datasets[], readiness_score, done_count}`
Each upload type: `{key, label, done, desc, columns}` for `sales`, `inventory`,
`menu`, `orders`, `customers`.

### `POST /api/uploads/<upload_type>/` — step 1: validate
`multipart/form-data` with a `file` field (`.csv`, `.xlsx`, `.xls`).

Response `200` (≤5000 rows):
```json
{
  "status": "ok", "row_count": 130, "upload_token": "hex",
  "preview_rows": [["2024-01-01", "Masala Dosa", "5", "600"]],
  "preview_cols": ["date", "item_name", "quantity", "revenue"],
  "columns": ["date", "item_name", "quantity", "revenue", "cost"],
  "row_errors": ["Row 12: \"date\" value \"xx\" is not a valid date."],
  "has_errors": false, "upload_type": "sales", "filename": "sales.csv"
}
```
Nothing is written to MongoDB at this stage. The parsed rows are held in the
Django cache for 10 minutes under `upload_token`.

Files over 5000 rows skip the preview and commit immediately, returning
`{ok: true, row_count, committed_immediately: true}` — same as the old view.

Response `400`: `{"error": "Missing required column(s): ..."}` — column
validation, aliasing (`qty`→`quantity`, `product`→`item_name`, …), and
date/numeric type checks are unchanged from `onboarding/services.py`.

### `POST /api/uploads/<upload_type>/` — step 2: commit
Request: `{upload_token, confirm: true}`
Response: `{ok: true, row_count}`. Registers the dataset in `uploaded_datasets`
and inserts normalized documents into the target collection.
`400` if the token expired.

### `GET /api/uploads/<upload_type>/template/`
Returns a `text/csv` attachment with the correct headers and two example rows.

---

## Menu (catalog)

### `GET /api/menu/?category=<optional>`
Response: `{items[], categories[]}`. Item: `{id, name, category, price, cost, description, is_available, recipe[]}`.
Recipe entry: `{ingredient, quantity, unit}` — this is what drives inventory auto-deduction on orders.

### `POST /api/menu/`
Request: `{name, category?, price?, cost?, description?, is_available?, recipe?[]}`. `name` required.

### `GET | PATCH | DELETE /api/menu/<item_id>/`
`PATCH` accepts any subset of the create fields. `DELETE` returns `204`.

---

## Inventory

### `GET /api/inventory/`
Response: `{items[], low_stock_count, expiring_count}`. Each item is annotated
server-side with `low_stock` (quantity ≤ reorder_level), `days_to_expiry`, and
`expiring_soon` (≤7 days).

### `POST /api/inventory/`
Upsert by `item_name` within the business (same as the old add-stock form).
Request: `{item_name, quantity?, unit?, cost_per_unit?, reorder_level?, expiry_date?, category?, supplier?}`

### `GET | PATCH | DELETE /api/inventory/<item_id>/`

---

## Orders

### `GET /api/orders/?status=<optional>`
Response: `{orders[], statuses[], counts{}}`. Latest 100, newest first.
`statuses` = `pending | preparing | ready | delivered | cancelled`.

### `POST /api/orders/`
Request:
```json
{"order_type": "dine_in", "table_no": "4", "customer_name": "Riya",
 "notes": "", "items": [{"item_id": "<menu item id>", "quantity": 2}]}
```
`order_type` ∈ `dine_in | takeaway | delivery | qr | phone`.
Prices come from the server-side menu lookup — the client cannot set a price.
**Side effect:** ingredients are auto-deducted from inventory via each item's recipe.
`400` if no valid line items resolve.

### `GET /api/orders/<order_id>/`
### `PATCH /api/orders/<order_id>/status/`
Request: `{status}` → `{status}`. `400` on an unknown status.

---

## Customers

### `GET /api/customers/?segment=<optional>`
Response: `{customers[], segments: ["VIP","Regular","Inactive"]}`.
`segment` is computed, not stored: VIP if spend ≥ 5000 or visits ≥ 20; Regular if visits ≥ 5; else Inactive.

### `POST /api/customers/`
Request: `{name, phone?, email?, notes?}`. `visit_count`/`total_spend` start at 0 and are system-managed.

### `GET /api/customers/<customer_id>/`
Response: the customer plus `recent_orders[]` (last 10, matched by customer name).

### `PATCH /api/customers/<customer_id>/`
Profile fields only (`name`, `phone`, `email`, `notes`). `visit_count` and
`total_spend` are deliberately not writable.

---

## Staff

### `GET /api/staff/`
Response: `{employees[]}`.

### `POST /api/staff/`
Request: `{name, role?, phone?, email?, salary?, join_date?}`. Created `active`.

### `PATCH | DELETE /api/staff/<employee_id>/`
`PATCH` also accepts `status`.

### `GET /api/staff/attendance/`
Response: `{employees[], today}` — active employees with today's `att_status`.

### `POST /api/staff/attendance/`
Request: `{"statuses": {"<employee_id>": "present"}}` — bulk upsert for today.
Response: `{ok: true, date}`.

---

## Suppliers

### `GET | POST /api/suppliers/`
Request: `{name, contact_person?, phone?, email?, address?, products?, payment_terms?}`.

### `PATCH | DELETE /api/suppliers/<supplier_id>/`

### `GET /api/suppliers/purchase-orders/`
Response: `{suppliers[], purchase_orders[]}` (latest 50).

### `POST /api/suppliers/purchase-orders/`
Request: `{supplier_id, supplier_name, items, total_amount}`. Created `pending`.
Note `items` is a free-text string in the current data model.

---

## Analytics

### `GET /api/analytics/?period=7|30|90|365`
`period` defaults to `30`. If there is no usable sales data: `{"has_data": false}`
— and the frontend must show the upload prompt.

Otherwise:
```json
{
  "has_data": true, "period": "30",
  "kpis": {"total_revenue": 0, "total_cost": 0, "total_profit": 0,
           "total_orders": 0, "avg_order_value": 0, "wow_change": 0},
  "chart_data": {
    "daily_labels": [], "daily_revenue": [], "daily_profit": [],
    "top_items_labels": [], "top_items_revenue": [],
    "dow_labels": ["Monday"], "dow_data": [], "hour_data": []
  }
}
```
`wow_change` is the percentage change against the preceding equal-length period.
`hour_data` is empty unless the uploaded data carries a time component.

---

## ML / forecasting

### `GET /api/ml/status/`
Response: `{sales_count, has_enough, latest, insights[]}`.
`has_enough` is `sales_count >= 30` — **this is the data gate**. The frontend
must not offer or fake an analysis when it is `false`.

### `POST /api/ml/run/`
Runs the full pipeline synchronously (forecast, profitability, waste, health score).
`400` with an explanatory `error` if under 30 sales records or the pipeline
raises a data-insufficiency `ValueError`; `500` on unexpected failure.
Response `200`: `{ok: true}`.

### `GET /api/ml/results/`
`404` `{"error": "No analysis results yet. Run the analysis first."}` when nothing has been run.
Otherwise: `{latest, insights[], forecast_dates[], forecast_values[], profitability,
stars[], plowhorses[], puzzles[], dogs[], health, waste_items[]}`
(the Stars/Plowhorses/Puzzles/Dogs menu-engineering matrix).

### `GET /api/ml/insights/`
Response: `{has_insights, insights[], by_category{}}`.

---

## Assistant

### `GET /api/assistant/status/`
Response: `{has_data, starter_chips[], llm_enabled}`. Chips are generated from
what data the business actually has.

### `POST /api/assistant/chat/`
Request: `{message}`
Response: `{reply, chips[], intent, needs_clarification}`

The role sent to the engine comes from the server-resolved `Membership`, never
from the request body. Prompt-injection screening, per-user rate limiting
(40/min), the identical-question cache, and conversation memory for follow-ups
all run inside `assistant/engine.py` unchanged. No LLM ever computes a number —
metrics come from deterministic tool functions.

### `POST /api/assistant/feedback/`
Request: `{rating: "up"|"down", question?, answer?}` → `{ok: true}`.
A `down` rating also writes to the gap log.

---

## Reports

These return binary files, so they are plain Django views with manual JWT
authentication rather than DRF views. Send the same `Authorization` and
`X-Business-Id` headers.

### `GET /api/reports/status/`
Response: `{has_sales, has_inventory, has_customers, has_staff, has_orders}` —
use it to decide which report cards to render.

### `GET /api/reports/export/<report_type>/<fmt>/?period=<optional>`
`report_type` ∈ `sales | inventory | customers | staff | orders`
`fmt` ∈ `excel | pdf`
`period` (sales only) ∈ `7 | 30 | 90 | 365`, default `30`.

Returns an `.xlsx` (openpyxl) or `.pdf` (reportlab) attachment.
`404` if that collection has no data; `503` if reportlab isn't installed.

---

## Notifications

### `GET /api/notifications/`
Regenerates alert conditions (low stock, expiry, waste risk, low health score),
deduplicated against the last 24 hours, then returns
`{notifications[], unread}` — latest 50.

### `POST /api/notifications/<notif_id>/read/` → `{ok: true}`
### `POST /api/notifications/mark-all-read/` → `{ok: true}`
