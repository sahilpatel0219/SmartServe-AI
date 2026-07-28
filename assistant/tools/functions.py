"""
The deterministic tool registry — one function per analytics capability.

Rules honored here:
  • Numbers are computed in Python from the business's real data. Nothing is
    invented; missing data yields `data_sufficient: False` with a clear reason.
  • `business_id` is injected by the orchestrator and applied at the query layer
    (datasource) — never supplied by the model.
  • Role checks are enforced INSIDE financial tools (Staff can't get profit /
    margin / cost / item profitability).
  • Every function returns a structured dict, never a formatted string.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from assistant import entities
from assistant.guards import check_access
from assistant.tools import datasource

WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
_SALES_METRICS = {'revenue', 'quantity', 'cost', 'profit', 'margin', 'orders'}


# ── result helpers ───────────────────────────────────────────────────────────
def _win(start: date | None, end: date | None) -> dict | None:
    if not start or not end:
        return None
    return {'start': start.isoformat(), 'end': end.isoformat(),
            'label': entities.range_label(start, end)}


def _ok(**kw) -> dict:
    r = {'ok': True, 'denied': False, 'data_sufficient': True, 'note': None}
    r.update(kw)
    return r


def _denied(reason: str, **kw) -> dict:
    return {'ok': False, 'denied': True, 'data_sufficient': False, 'reason': reason, **kw}


def _insufficient(need: str, **kw) -> dict:
    r = {'ok': True, 'denied': False, 'data_sufficient': False, 'need': need}
    r.update(kw)
    return r


def _window(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    d = df.dropna(subset=['_date'])
    return d[(d['_date'] >= start) & (d['_date'] <= end)]


def _compute_metric(d: pd.DataFrame, metric: str) -> tuple[float, bool, str | None]:
    """Return (value, data_sufficient, note) for a sales metric over rows `d`."""
    if metric == 'revenue':
        return float(d['revenue'].sum()), True, None
    if metric == 'quantity':
        return float(d['quantity'].sum()), True, None
    if metric == 'cost':
        return float(d['cost'].sum()), True, None
    if metric == 'profit':
        cost = float(d['cost'].sum())
        if cost == 0:
            return 0.0, False, "No cost data in your sales uploads, so profit can't be computed."
        return float(d['revenue'].sum()) - cost, True, None
    if metric == 'margin':
        rev = float(d['revenue'].sum())
        cost = float(d['cost'].sum())
        if rev == 0 or cost == 0:
            return 0.0, False, "Need both revenue and cost to compute margin."
        return round((rev - cost) / rev * 100, 1), True, None
    if metric == 'orders':
        ids = d['order_id'].dropna()
        if len(ids) > 0:
            return int(ids.nunique()), True, None
        return int(len(d)), True, "Counting sales line-items (no order_id column in your data)."
    raise ValueError(f'unknown metric {metric}')


# ── 1. get_metric ────────────────────────────────────────────────────────────
def get_metric(business_id, role, metric, start, end, item=None, category=None) -> dict:
    """Total of a metric (revenue, orders, quantity, profit, margin, cost) over a
    date range, optionally filtered to one item or category."""
    if metric not in _SALES_METRICS:
        return _insufficient('valid_metric', metric=metric, window=_win(start, end))
    ok, reason = check_access(role, metric=metric)
    if not ok:
        return _denied(reason, metric=metric, window=_win(start, end))
    df = datasource.load_sales(business_id)
    if df.empty:
        return _insufficient('sales', metric=metric, window=_win(start, end))
    d = _window(df, start, end)
    if item:
        d = d[d['item_name'] == item]
    if category:
        d = d[d['category'] == category]
    value, suff, note = _compute_metric(d, metric)
    return _ok(metric=metric, value=value, item=item, category=category,
               rows=int(len(d)), window=_win(start, end), data_sufficient=suff, note=note)


# ── 2. compare_periods ───────────────────────────────────────────────────────
def compare_periods(business_id, role, metric, period_a, period_b, item=None) -> dict:
    """Compare a metric between two periods. `period_a`/`period_b` are (start, end)
    date tuples. Returns both values, the delta, and the % change."""
    a = get_metric(business_id, role, metric, period_a[0], period_a[1], item=item)
    if a.get('denied'):
        return a
    b = get_metric(business_id, role, metric, period_b[0], period_b[1], item=item)
    va, vb = a.get('value', 0), b.get('value', 0)
    delta = va - vb
    pct = round((delta / vb * 100), 1) if vb else None
    return _ok(metric=metric, item=item,
               period_a={'value': va, 'window': a.get('window')},
               period_b={'value': vb, 'window': b.get('window')},
               delta=delta, pct_change=pct,
               direction='up' if delta > 0 else 'down' if delta < 0 else 'flat',
               data_sufficient=a.get('data_sufficient') and b.get('data_sufficient'))


# ── 3. rank_items ────────────────────────────────────────────────────────────
def rank_items(business_id, role, metric, start, end, limit=5, ascending=False) -> dict:
    """Rank menu items by a metric over a range (top or bottom `limit`)."""
    ok, reason = check_access(role, metric=metric)
    if not ok:
        return _denied(reason, metric=metric, window=_win(start, end))
    df = datasource.load_sales(business_id)
    if df.empty:
        return _insufficient('sales', metric=metric, window=_win(start, end))
    d = _window(df, start, end)
    if d.empty:
        return _ok(metric=metric, items=[], window=_win(start, end), data_sufficient=False,
                   note='No sales in that window.')
    if metric in ('profit', 'margin'):
        grp = d.groupby('item_name').apply(
            lambda g: _compute_metric(g, metric)[0], include_groups=False)
    else:
        col = {'revenue': 'revenue', 'quantity': 'quantity', 'cost': 'cost'}.get(metric, 'revenue')
        grp = d.groupby('item_name')[col].sum()
    grp = grp.sort_values(ascending=ascending).head(limit)
    items = [{'item': str(k), 'value': float(v)} for k, v in grp.items()]
    return _ok(metric=metric, ascending=ascending, items=items, window=_win(start, end))


# ── 4. get_trend ─────────────────────────────────────────────────────────────
def get_trend(business_id, role, metric, start, end, granularity='day') -> dict:
    """A time series of a metric across a range, bucketed by day / week / month."""
    ok, reason = check_access(role, metric=metric)
    if not ok:
        return _denied(reason, metric=metric, window=_win(start, end))
    df = datasource.load_sales(business_id)
    if df.empty:
        return _insufficient('sales', metric=metric, window=_win(start, end))
    d = _window(df, start, end).copy()
    if d.empty:
        return _ok(metric=metric, series=[], window=_win(start, end), data_sufficient=False)
    ts = pd.to_datetime(d['_date'])
    if granularity == 'month':
        key = ts.dt.to_period('M').astype(str)
    elif granularity == 'week':
        key = ts.dt.to_period('W').astype(str)
    else:
        key = ts.dt.strftime('%Y-%m-%d')
    d = d.assign(_bucket=key.values)
    series = []
    for b, g in d.groupby('_bucket'):
        val, _, _ = _compute_metric(g, metric)
        series.append({'bucket': str(b), 'value': float(val)})
    series.sort(key=lambda x: x['bucket'])
    # simple direction over the series
    direction = 'flat'
    if len(series) >= 2:
        direction = 'up' if series[-1]['value'] > series[0]['value'] else \
                    'down' if series[-1]['value'] < series[0]['value'] else 'flat'
    return _ok(metric=metric, granularity=granularity, series=series,
               direction=direction, window=_win(start, end))


# ── 5. get_sales_breakdown ───────────────────────────────────────────────────
def get_sales_breakdown(business_id, role, start, end, by='day') -> dict:
    """Break revenue down by day / weekday / category / hour over a range."""
    df = datasource.load_sales(business_id)
    if df.empty:
        return _insufficient('sales', by=by, window=_win(start, end))
    d = _window(df, start, end).copy()
    if d.empty:
        return _ok(by=by, breakdown=[], window=_win(start, end), data_sufficient=False)
    ts = pd.to_datetime(d['_date'])
    if by == 'weekday':
        d = d.assign(_k=ts.dt.day_name().values)
        order = WEEKDAYS
    elif by == 'category':
        d = d.assign(_k=d['category'].fillna('Uncategorized').astype(str))
        order = None
    elif by == 'hour':
        if d['_hour'].isna().all():
            return _insufficient('hourly_timestamps', by=by, window=_win(start, end),
                                 note="Your sales data has dates but no time-of-day, so hourly breakdown isn't available.")
        d = d.assign(_k=d['_hour'].astype('Int64').astype(str))
        order = None
    else:  # day
        d = d.assign(_k=ts.dt.strftime('%Y-%m-%d').values)
        order = None
    grp = d.groupby('_k')['revenue'].sum()
    if order:
        grp = grp.reindex([x for x in order if x in grp.index])
    breakdown = [{'key': str(k), 'revenue': float(v)} for k, v in grp.items()]
    return _ok(by=by, breakdown=breakdown, window=_win(start, end))


# ── 6. inventory tools ───────────────────────────────────────────────────────
def _inv_num(v, default=0.0):
    try:
        return float(str(v).replace(',', ''))
    except (TypeError, ValueError):
        return default


def get_low_stock(business_id, role=None) -> dict:
    """Inventory items at or below their reorder level."""
    inv = datasource.load_inventory(business_id)
    if not inv:
        return _insufficient('inventory')
    low = []
    for i in inv:
        qty = _inv_num(i.get('quantity'), 1e9)
        reorder = _inv_num(i.get('reorder_level'), 0)
        if qty <= reorder:
            low.append({'item': i.get('item_name', '?'), 'quantity': qty,
                        'reorder_level': reorder, 'unit': i.get('unit', '')})
    low.sort(key=lambda x: x['quantity'])
    return _ok(items=low, count=len(low), total_tracked=len(inv))


def get_expiring_soon(business_id, role=None, days=3) -> dict:
    """Inventory items expiring within `days` days (needs expiry dates)."""
    inv = datasource.load_inventory(business_id)
    if not inv:
        return _insufficient('inventory')
    today = date.today()
    horizon = today + timedelta(days=days)
    soon, has_expiry = [], False
    for i in inv:
        exp = i.get('expiry_date')
        if not exp:
            continue
        has_expiry = True
        try:
            ed = pd.to_datetime(str(exp), errors='coerce')
            if pd.isna(ed):
                continue
            ed = ed.date()
        except Exception:
            continue
        if ed <= horizon:
            soon.append({'item': i.get('item_name', '?'), 'expiry_date': ed.isoformat(),
                         'days_left': (ed - today).days, 'quantity': _inv_num(i.get('quantity'))})
    if not has_expiry:
        return _insufficient('expiry_dates',
                             note='Your inventory has no expiry_date column, so expiry alerts are unavailable.')
    soon.sort(key=lambda x: x['days_left'])
    return _ok(days=days, items=soon, count=len(soon))


def get_reorder_suggestions(business_id, role=None) -> dict:
    """Items to reorder now (at/below reorder level), with a suggested quantity."""
    low = get_low_stock(business_id, role)
    if not low.get('data_sufficient', True) is False and low.get('ok'):
        suggestions = []
        for it in low.get('items', []):
            # suggest topping up to ~2x reorder level (simple, transparent rule)
            target = max(it['reorder_level'] * 2, it['reorder_level'] + 1)
            suggestions.append({**it, 'suggested_order': round(target - it['quantity'], 2)})
        return _ok(items=suggestions, count=len(suggestions))
    return low


# ── 7. customers ─────────────────────────────────────────────────────────────
def _segment(visits, spend):
    if spend >= 5000 or visits >= 20:
        return 'VIP'
    if visits >= 5:
        return 'Regular'
    return 'Inactive'


def get_customer_stats(business_id, role=None, segment=None) -> dict:
    """Customer counts by segment, plus top spenders (aggregates only — no PII sent onward)."""
    custs = datasource.load_customers(business_id)
    if not custs:
        return _insufficient('customers')
    buckets = {'VIP': 0, 'Regular': 0, 'Inactive': 0}
    enriched = []
    for c in custs:
        seg = _segment(_inv_num(c.get('visit_count')), _inv_num(c.get('total_spend')))
        buckets[seg] += 1
        enriched.append((c.get('name', '?'), _inv_num(c.get('total_spend')), seg))
    top = sorted(enriched, key=lambda x: x[1], reverse=True)[:5]
    result = _ok(total=len(custs), segments=buckets,
                 top_spenders=[{'name': n, 'total_spend': s} for n, s, _ in top])
    if segment:
        result['segment'] = segment
        result['segment_count'] = buckets.get(segment, 0)
    return result


# ── 8. peak times ────────────────────────────────────────────────────────────
def get_peak_times(business_id, role=None, start=None, end=None) -> dict:
    """Busiest weekdays (and hours, if the data has timestamps) by revenue."""
    df = datasource.load_sales(business_id)
    if df.empty:
        return _insufficient('sales')
    if start and end:
        d = _window(df, start, end)
    else:
        d = df.dropna(subset=['_date'])
    if d.empty:
        return _insufficient('sales')
    ts = pd.to_datetime(d['_date'])
    wd = d.assign(_wd=ts.dt.day_name().values).groupby('_wd')['revenue'].sum()
    wd = wd.reindex([x for x in WEEKDAYS if x in wd.index])
    weekday = [{'weekday': k, 'revenue': float(v)} for k, v in wd.items()]
    busiest = max(weekday, key=lambda x: x['revenue']) if weekday else None
    hours = None
    if not d['_hour'].isna().all():
        hr = d.dropna(subset=['_hour']).groupby('_hour')['revenue'].sum().sort_values(ascending=False)
        hours = [{'hour': int(k), 'revenue': float(v)} for k, v in hr.head(3).items()]
    return _ok(weekday=weekday, busiest_weekday=busiest, peak_hours=hours,
               window=_win(start, end) if start else None)


# ── 9. item profitability (financial → manager+) ─────────────────────────────
def get_item_profitability(business_id, role, item=None) -> dict:
    """Per-item revenue, cost, profit, and margin — with a menu-engineering
    classification from the latest AI analysis when available."""
    ok, reason = check_access(role, intent='profitability')
    if not ok:
        return _denied(reason)
    df = datasource.load_sales(business_id)
    if df.empty:
        return _insufficient('sales')
    if df['cost'].sum() == 0:
        return _insufficient('cost', note='No cost column in your sales data, so margins are unavailable.')
    d = df if item is None else df[df['item_name'] == item]
    rows = []
    for name, g in d.groupby('item_name'):
        rev, cost = float(g['revenue'].sum()), float(g['cost'].sum())
        margin = round((rev - cost) / rev * 100, 1) if rev else 0.0
        rows.append({'item': str(name), 'revenue': rev, 'cost': cost,
                     'profit': rev - cost, 'margin_pct': margin})
    rows.sort(key=lambda x: x['profit'], reverse=True)
    return _ok(items=rows if item is None else rows[:1], count=len(rows))


# ── 10. AI-derived tools (read the latest analysis; never recompute here) ─────
def _confidence_from_history(training_rows, explicit_error=None) -> dict:
    """Honest confidence indicator. If the model reported a validated error we use
    it; otherwise we grade by how much history it trained on (volume, NOT accuracy)
    and say so plainly — never overstating certainty."""
    if explicit_error is not None:
        return {'label': 'measured', 'error': explicit_error,
                'note': 'Based on the model\'s reported error on held-out data.'}
    tr = training_rows or 0
    label = 'low' if tr < 30 else 'moderate' if tr < 90 else 'good'
    return {'label': label, 'history_days': tr,
            'note': 'Confidence reflects how much of your history the model trained on '
                    f'({tr} days), not a validated error rate.'}


def get_forecast(business_id, role=None, horizon=7, item=None) -> dict:
    """Latest sales forecast with a confidence indicator and the amount of history
    it is based on. Never presents a forecast as certain."""
    fc = datasource.latest_forecast(business_id) or datasource.latest_full_analysis(business_id)
    if not fc:
        return _insufficient('forecast',
                             note='No forecast yet — you need ~30+ days of sales, then run the AI analysis.')
    data = fc.get('data', fc)
    daily = data.get('daily_forecast') or fc.get('forecast', {}).get('daily') or []
    total = fc.get('forecast', {}).get('total_forecast')
    if total is None and daily:
        total = sum(p.get('predicted_revenue', 0) for p in daily)
    training_rows = data.get('training_rows') or fc.get('forecast', {}).get('training_rows')
    explicit_error = fc.get('forecast', {}).get('error') or data.get('error')
    return _ok(horizon=horizon, item=item, daily=daily, total=total,
               training_rows=training_rows,
               confidence=_confidence_from_history(training_rows, explicit_error),
               model=data.get('model', 'xgboost'),
               caveat='Forecasts are estimates from your own history, not guarantees.')


# ── 12. diagnostic composite (the "why..." case) ─────────────────────────────
def _period_totals(d: pd.DataFrame):
    total = float(d['revenue'].sum())
    ids = d['order_id'].dropna()
    orders = int(ids.nunique()) if len(ids) else int(len(d))
    ticket = (total / orders) if orders else 0.0
    return total, orders, ticket


def explain_sales_change(business_id, role, period_a, period_b=None) -> dict:
    """Diagnose a revenue change for period_a. Confirms the change is real (vs the
    same-weekday recent average for a single day, else vs period_b), then
    decomposes it by item to surface the biggest movers. Reports only what the
    data shows and flags untracked factors as unverified — it never invents a cause."""
    df = datasource.load_sales(business_id)
    if df.empty:
        return _insufficient('sales')
    a_start, a_end = period_a
    a = _window(df, a_start, a_end)

    baseline_kind = 'period'
    if period_b:
        b_start, b_end = period_b
        base = _window(df, b_start, b_end)
        base_total, base_orders, base_ticket = _period_totals(base)
        base_items = base.groupby('item_name')['revenue'].sum()
        base_label = entities.range_label(b_start, b_end)
    elif a_start == a_end:
        # same-weekday recent average (the correct baseline for one day)
        baseline_kind = 'weekday_avg'
        wd = a_start.weekday()
        prior = df.dropna(subset=['_date'])
        prior = prior[(prior['_date'] < a_start) &
                      (pd.to_datetime(prior['_date']).dt.weekday == wd)]
        if prior.empty:
            return _insufficient('history',
                                 note=f'No earlier {a_start.strftime("%A")}s to compare against yet.')
        day_totals = prior.groupby('_date')['revenue'].sum()
        base_total = float(day_totals.mean())
        n_days = len(day_totals)
        base_orders = base_ticket = None
        base_items = prior.groupby('item_name')['revenue'].sum() / n_days  # per-weekday average
        base_label = f'the average {a_start.strftime("%A")} ({n_days} prior)'
    else:
        b_start, b_end = _default_window_prev(a_start, a_end)
        base = _window(df, b_start, b_end)
        base_total, base_orders, base_ticket = _period_totals(base)
        base_items = base.groupby('item_name')['revenue'].sum()
        base_label = entities.range_label(b_start, b_end)

    a_total, a_orders, a_ticket = _period_totals(a)
    delta = a_total - base_total
    pct = round(delta / base_total * 100, 1) if base_total else None
    direction = 'down' if delta < 0 else 'up' if delta > 0 else 'flat'

    a_items = a.groupby('item_name')['revenue'].sum()
    all_items = a_items.reindex(a_items.index.union(base_items.index)).fillna(0)
    base_al = base_items.reindex(all_items.index).fillna(0)
    item_diff = (all_items - base_al).sort_values()
    top_drops = [{'item': str(k), 'delta': float(v)} for k, v in item_diff.head(3).items() if v < 0]
    top_gains = [{'item': str(k), 'delta': float(v)} for k, v in item_diff.tail(3).items() if v > 0]
    top_gains.reverse()

    return _ok(
        baseline_kind=baseline_kind, direction=direction,
        a_total=a_total, base_total=round(base_total, 2), delta=round(delta, 2), pct_change=pct,
        a_window=_win(a_start, a_end), base_label=base_label,
        a_orders=a_orders, base_orders=base_orders,
        a_ticket=round(a_ticket, 2), base_ticket=round(base_ticket, 2) if base_ticket else None,
        top_drops=top_drops, top_gains=top_gains,
        untracked=['weather', 'local events/festivals', 'foot traffic'],
    )


def _default_window_prev(start: date, end: date):
    span = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    return prev_end - timedelta(days=span - 1), prev_end


def get_waste_risk(business_id, role=None) -> dict:
    """Estimated food-waste loss and the at-risk items from the latest analysis."""
    pred = datasource.latest_full_analysis(business_id)
    if not pred:
        return _insufficient('analysis',
                             note='Run the AI analysis to estimate waste risk.')
    waste = pred.get('waste', {})
    return _ok(estimated_loss=waste.get('estimated_loss_inr', 0),
               items=waste.get('high_waste_items', [])[:8])


def get_health_score(business_id, role=None) -> dict:
    """Business health score (0–100) and its component breakdown."""
    pred = datasource.latest_full_analysis(business_id)
    if not pred:
        return _insufficient('analysis', note='Run the AI analysis to get a health score.')
    hs = pred.get('health_score', {})
    score = hs.get('total_score')
    if score is None:
        return _insufficient('analysis')
    comps = hs.get('components', {})
    weakest = min(comps, key=comps.get) if comps else None
    return _ok(score=round(float(score), 1), components=comps, weakest=weakest)


# ── 11. data availability ────────────────────────────────────────────────────
def get_data_availability(business_id, role=None) -> dict:
    """What data is uploaded, its date coverage, and any obvious gaps."""
    df = datasource.load_sales(business_id)
    inv = datasource.load_inventory(business_id)
    custs = datasource.load_customers(business_id)
    pred = datasource.latest_full_analysis(business_id)
    coverage = None
    if not df.empty and df['_date'].notna().any():
        dates = sorted(d for d in df['_date'].dropna().unique())
        coverage = {'start': dates[0].isoformat(), 'end': dates[-1].isoformat(),
                    'days_with_data': len(set(dates))}
    return _ok(has_sales=not df.empty, sales_rows=int(len(df)),
               has_cost=(not df.empty and float(df['cost'].sum()) > 0),
               has_inventory=bool(inv), inventory_items=len(inv),
               has_customers=bool(custs), customers=len(custs),
               has_analysis=bool(pred), coverage=coverage)
