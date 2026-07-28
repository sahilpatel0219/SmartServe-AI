"""
Answer composition — turns a tool's STRUCTURED result into a short, natural
chat reply (templated). This is the fallback-mode phrasing and also the
guaranteed floor when the LLM is unavailable.

Rules: lead with the direct answer; state the period used; ₹ with thousands
separators; percentages to one decimal; forecasts always carry a caveat; if
data is missing, say exactly what to upload. Returns (text, chips) where chips
are 2–3 suggested follow-up questions.
"""
from __future__ import annotations

UPLOAD_HINT = "Upload it from Data Upload to unlock this."

_NEED_MESSAGES = {
    'sales': "I don't have any sales data yet.",
    'cost': "Your sales data has no cost column, so I can't work out profit or margin.",
    'inventory': "I don't have inventory data yet.",
    'expiry_dates': "Your inventory has no expiry dates, so I can't flag what's expiring.",
    'hourly_timestamps': "Your sales have dates but no time-of-day, so hourly views aren't available.",
    'customers': "I don't have any customer data yet.",
    'analysis': "There's no AI analysis yet — run it from the AI Engine page.",
    'forecast': "There's no forecast yet. You need ~30+ days of sales, then run the AI analysis.",
    'valid_metric': "I can look at revenue, orders, quantity, profit, margin or cost.",
}

_METRIC_NOUN = {'revenue': 'revenue', 'profit': 'gross profit', 'cost': 'cost',
                'quantity': 'units sold', 'orders': 'orders', 'margin': 'margin'}


# ── formatting ───────────────────────────────────────────────────────────────
def money(v) -> str:
    try:
        return f"₹{float(v):,.0f}"
    except (TypeError, ValueError):
        return "₹0"


def pct(v) -> str:
    return f"{float(v):.1f}%"


def _win(result) -> str:
    w = result.get('window')
    return f" in {w['label']}" if w and w.get('label') else ""


def _metric_value(metric, value) -> str:
    if metric in ('revenue', 'profit', 'cost'):
        return money(value)
    if metric == 'margin':
        return pct(value)
    if metric == 'orders':
        return f"{int(value):,} orders"
    if metric == 'quantity':
        return f"{int(value):,} units"
    return f"{value:,}"


def _denied_or_insufficient(result) -> str | None:
    if result.get('denied'):
        return result.get('reason')
    if result.get('data_sufficient') is False:
        need = result.get('need')
        base = _NEED_MESSAGES.get(need) or result.get('note') or "I don't have enough data for that yet."
        if need in ('sales', 'inventory', 'customers'):
            return f"{base} {UPLOAD_HINT}"
        return base
    return None


# ── per-intent renderers ─────────────────────────────────────────────────────
def render_metric(result, entities) -> str:
    bad = _denied_or_insufficient(result)
    if bad:
        return bad
    metric = result['metric']
    val = _metric_value(metric, result['value'])
    scope = ''
    if result.get('item'):
        scope = f" for {result['item']}"
    elif result.get('category'):
        scope = f" in {result['category']}"
    verb = {'revenue': 'made', 'profit': 'kept', 'orders': 'took', 'quantity': 'sold'}.get(metric)
    if metric == 'margin':
        return f"Your margin{scope} was {val}{_win(result)}."
    if verb:
        return f"You {verb} {val}{scope}{_win(result)}."
    return f"{_METRIC_NOUN.get(metric, metric).title()}{scope}: {val}{_win(result)}."


def render_ranking(result, entities) -> str:
    bad = _denied_or_insufficient(result)
    if bad:
        return bad
    items = result.get('items', [])
    if not items:
        return f"No sales to rank{_win(result)}."
    metric = result['metric']
    label = 'lowest' if result.get('ascending') else 'top'
    parts = ", ".join(f"{i['item']} ({_metric_value(metric, i['value'])})" for i in items)
    return f"Your {label} items by {_METRIC_NOUN.get(metric, metric)}{_win(result)}: {parts}."


def render_comparison(result, entities) -> str:
    bad = _denied_or_insufficient(result)
    if bad:
        return bad
    metric = result['metric']
    a, b = result['period_a'], result['period_b']
    va, vb = _metric_value(metric, a['value']), _metric_value(metric, b['value'])
    if result.get('pct_change') is None:
        return f"{_METRIC_NOUN.get(metric, metric).title()}: {va} ({a['window']['label']}) vs {vb} ({b['window']['label']})."
    d = result['direction']
    word = 'up' if d == 'up' else 'down' if d == 'down' else 'unchanged'
    return (f"{_METRIC_NOUN.get(metric, metric).title()} is {word} {pct(abs(result['pct_change']))} — "
            f"{va} in {a['window']['label']} vs {vb} in {b['window']['label']}.")


def render_trend(result, entities) -> str:
    bad = _denied_or_insufficient(result)
    if bad:
        return bad
    s = result.get('series', [])
    if len(s) < 2:
        return f"Not enough points to show a trend{_win(result)}."
    metric = result['metric']
    first, last = s[0], s[-1]
    d = result['direction']
    word = {'up': 'rising', 'down': 'falling', 'flat': 'roughly flat'}[d]
    return (f"{_METRIC_NOUN.get(metric, metric).title()} is {word}{_win(result)} — "
            f"from {_metric_value(metric, first['value'])} to {_metric_value(metric, last['value'])}.")


def render_forecast(result, entities) -> str:
    bad = _denied_or_insufficient(result)
    if bad:
        return bad
    total = result.get('total')
    hist = result.get('training_rows')
    hist_txt = f" based on {hist} days of your history" if hist else ""
    lead = f"Forecast for the next {result.get('horizon', 7)} days: {money(total)}{hist_txt}." if total else \
           "I have a forecast on file — see the AI Results page for the daily chart."
    conf = result.get('confidence') or {}
    conf_txt = f" Confidence: {conf['label']} — {conf['note']}" if conf.get('label') else ""
    return f"{lead} Treat it as an estimate from your own data, not a guarantee.{conf_txt}"


def render_diagnostic(result, entities) -> str:
    bad = _denied_or_insufficient(result)
    if bad:
        return bad
    d = result['direction']
    word = {'down': 'down', 'up': 'up', 'flat': 'flat'}[d]
    pctxt = f" {abs(result['pct_change']):.1f}%" if result.get('pct_change') is not None else ""
    win = result.get('a_window', {}).get('label', 'that period')
    lead = (f"Revenue was {word}{pctxt} — {money(result['a_total'])} in {win} "
            f"vs {money(result['base_total'])} ({result['base_label']}).")
    drops = result.get('top_drops', [])
    gains = result.get('top_gains', [])
    if drops:
        lead += " Biggest drops: " + ", ".join(f"{x['item']} (−{money(abs(x['delta']))})" for x in drops) + "."
    if gains:
        lead += " Biggest gainers: " + ", ".join(f"{x['item']} (+{money(x['delta'])})" for x in gains) + "."
    if result.get('a_orders') is not None and result.get('base_orders') is not None:
        lead += f" Orders: {result['base_orders']} → {result['a_orders']}."
    lead += (" The data can't see " + ", ".join(result.get('untracked', [])) +
             " — treat those as possible but unverified factors.")
    return lead


def render_inventory_low(result, entities) -> str:
    bad = _denied_or_insufficient(result)
    if bad:
        return bad
    items = result.get('items', [])
    if not items:
        return f"Stock looks healthy — {result.get('total_tracked', 0)} items tracked, none below reorder level."
    names = ", ".join(f"{i['item']} ({i['quantity']:g}{(' ' + i['unit']) if i.get('unit') else ''})" for i in items[:8])
    return f"⚠️ {result['count']} item(s) at or below reorder level: {names}."


def render_reorder(result, entities) -> str:
    bad = _denied_or_insufficient(result)
    if bad:
        return bad
    items = result.get('items', [])
    if not items:
        return "Nothing needs reordering right now — all items are above their reorder level."
    names = ", ".join(f"{i['item']} (order ~{i['suggested_order']:g}{(' ' + i['unit']) if i.get('unit') else ''})" for i in items[:8])
    return f"Reorder now: {names}."


def render_expiring(result, entities) -> str:
    bad = _denied_or_insufficient(result)
    if bad:
        return bad
    items = result.get('items', [])
    if not items:
        return f"Nothing is expiring within {result.get('days', 3)} days."
    names = ", ".join(f"{i['item']} ({i['days_left']}d)" for i in items[:8])
    return f"{result['count']} item(s) expiring within {result.get('days', 3)} days: {names}."


def render_profitability(result, entities) -> str:
    bad = _denied_or_insufficient(result)
    if bad:
        return bad
    items = result.get('items', [])
    if not items:
        return "No item profitability to show yet."
    parts = ", ".join(f"{i['item']} ({money(i['profit'])} profit, {pct(i['margin_pct'])} margin)" for i in items[:5])
    return f"Most profitable items: {parts}."


def render_waste(result, entities) -> str:
    bad = _denied_or_insufficient(result)
    if bad:
        return bad
    loss = money(result.get('estimated_loss', 0))
    items = result.get('items', [])
    names = ", ".join(w.get('item', '') for w in items[:3])
    extra = f" At-risk: {names}." if names else ""
    return f"Estimated food-waste loss: {loss}.{extra}"


def render_customer(result, entities) -> str:
    bad = _denied_or_insufficient(result)
    if bad:
        return bad
    seg = result.get('segments', {})
    top = result.get('top_spenders', [])
    lead = f"You have {result['total']:,} customers — {seg.get('VIP', 0)} VIP, {seg.get('Regular', 0)} regular, {seg.get('Inactive', 0)} inactive."
    if 'segment_count' in result:
        lead = f"You have {result['segment_count']:,} {result['segment']} customer(s). " + lead
    if top:
        lead += f" Top spender: {top[0]['name']} ({money(top[0]['total_spend'])})."
    return lead


def render_staffing(result, entities) -> str:
    bad = _denied_or_insufficient(result)
    if bad:
        return bad
    busy = result.get('busiest_weekday')
    if not busy:
        return "I couldn't work out your busiest times from the data."
    txt = f"Your busiest weekday is {busy['weekday']} ({money(busy['revenue'])})."
    hours = result.get('peak_hours')
    if hours:
        txt += " Peak hours: " + ", ".join(f"{h['hour']}:00" for h in hours) + "."
    return txt


def render_health(result, entities) -> str:
    bad = _denied_or_insufficient(result)
    if bad:
        return bad
    score = result['score']
    label = ('Excellent' if score >= 80 else 'Good' if score >= 60 else
             'Fair' if score >= 40 else 'Needs attention')
    weak = result.get('weakest')
    extra = f" Weakest area: {weak.replace('_', ' ')}." if weak else ""
    return f"Your business health score is {score:g}/100 — {label}.{extra}"


# ── chips (follow-up suggestions) ────────────────────────────────────────────
_CHIPS = {
    'metric_lookup': ["How does that compare to last month?", "What are my top items?", "Show my sales forecast"],
    'ranking': ["Which items are least profitable?", "How is my best seller trending?", "What's my total revenue?"],
    'comparison': ["Why did it change?", "Break it down by item", "What about last week?"],
    'trend': ["What's driving the change?", "Show top items", "What's the forecast?"],
    'forecast': ["What should I reorder for that?", "Which items will sell most?", "How's my stock?"],
    'inventory': ["What's expiring soon?", "What should I reorder?", "How much am I wasting?"],
    'profitability': ["Should I raise any prices?", "What are my worst margins?", "What's my total profit?"],
    'waste': ["What's expiring soon?", "What should I reorder?", "How's my health score?"],
    'customer': ["Who are my top spenders?", "How many regulars?", "What's my busiest day?"],
    'staffing': ["What's my busiest day?", "How do weekdays compare to weekends?", "Show the sales trend"],
    'health': ["What's dragging my score down?", "How's my waste risk?", "What should I improve?"],
    'diagnostic': ["Break it down by category", "How does it compare to last month?", "What's the forecast?"],
}
_DEFAULT_CHIPS = ["What's my total revenue?", "What are my best sellers?", "How's my stock?"]


def chips_for(intent: str) -> list[str]:
    return _CHIPS.get(intent, _DEFAULT_CHIPS)
