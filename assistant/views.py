"""
AI Assistant: chat panel with pluggable LLM backend.
Falls back to a stats-based answerer when LLM_PROVIDER / LLM_API_KEY is not set.
"""
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from accounts.models import Membership
from mongo import collections as col
from django.conf import settings


def _get_business(request):
    from core.utils import get_active_business
    return get_active_business(request)


@login_required
def index_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    has_data = col.sales_records().count_documents({'business_id': bid}) > 0
    return render(request, 'assistant/index.html', {
        'business': business,
        'has_data': has_data,
        'llm_enabled': bool(getattr(settings, 'LLM_PROVIDER', '') and getattr(settings, 'LLM_API_KEY', '')),
    })


@login_required
@require_POST
def chat_view(request):
    business, _ = _get_business(request)
    if not business:
        return JsonResponse({'error': 'No active business'}, status=403)
    bid = business.mongo_id

    try:
        body = json.loads(request.body)
        question = str(body.get('message', '')).strip()
    except Exception:
        return JsonResponse({'error': 'Invalid request'}, status=400)

    if not question:
        return JsonResponse({'error': 'Empty message'}, status=400)

    reply = _answer(question, bid, business.name)
    return JsonResponse({'reply': reply})


def _answer(question: str, bid: str, biz_name: str) -> str:
    """Route to LLM or stats-based fallback."""
    provider = getattr(settings, 'LLM_PROVIDER', '').lower()
    api_key = getattr(settings, 'LLM_API_KEY', '')

    if provider == 'anthropic' and api_key:
        return _llm_anthropic(question, bid, biz_name, api_key)
    elif provider == 'openai' and api_key:
        return _llm_openai(question, bid, biz_name, api_key)
    else:
        return _stats_answer(question, bid, biz_name)


def _to_num(series):
    import pandas as pd
    return pd.to_numeric(series.astype(str).str.replace(',', ''), errors='coerce').fillna(0)


def _load_sales_df(bid):
    """Load sales records as a numeric-typed DataFrame (data is normalised on upload)."""
    import pandas as pd
    records = list(col.sales_records().find({'business_id': bid}))
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    for c in ['revenue', 'quantity', 'cost']:
        if c in df.columns:
            df[c] = _to_num(df[c])
    if 'date' in df.columns:
        df['_date'] = pd.to_datetime(df['date'], errors='coerce')
    if 'item_name' not in df.columns:
        df['item_name'] = ''
    return df


def _latest_pred(bid):
    return col.predictions().find_one(
        {'business_id': bid, 'type': 'full_analysis'}, sort=[('created_at', -1)]
    )


def _build_context(bid: str, biz_name: str) -> str:
    """Summarise key business metrics from MongoDB for LLM context."""
    ctx_parts = [f"Business: {biz_name}"]

    df = _load_sales_df(bid)
    if not df.empty and 'revenue' in df.columns:
        ctx_parts.append(f"Total sales line-items: {len(df)}")
        ctx_parts.append(f"Total revenue in dataset: ₹{df['revenue'].sum():,.0f}")
        ctx_parts.append(f"Average line-item value: ₹{df['revenue'].mean():,.0f}")
        if 'cost' in df.columns:
            ctx_parts.append(f"Gross profit: ₹{(df['revenue'].sum() - df['cost'].sum()):,.0f}")
        # Top items
        top = df.groupby('item_name')['revenue'].sum().nlargest(5)
        ctx_parts.append("Top items by revenue: " + ", ".join(f"{i} (₹{v:,.0f})" for i, v in top.items()))
        # Busiest day of week
        if '_date' in df.columns and df['_date'].notna().any():
            dow = df.dropna(subset=['_date']).groupby(df['_date'].dt.day_name())['revenue'].sum()
            if not dow.empty:
                ctx_parts.append(f"Busiest day: {dow.idxmax()}")

    # Orders / customers
    n_orders = col.orders().count_documents({'business_id': bid})
    if n_orders:
        ctx_parts.append(f"Orders on record: {n_orders}")
    n_cust = col.customers().count_documents({'business_id': bid})
    if n_cust:
        ctx_parts.append(f"Customers on record: {n_cust}")

    # Latest prediction
    pred = _latest_pred(bid)
    if pred:
        hs = pred.get('health_score', {}).get('total_score')
        if hs is not None:
            ctx_parts.append(f"Business health score: {hs:.1f}/100")
        total_fc = pred.get('forecast', {}).get('total_forecast')
        if total_fc:
            ctx_parts.append(f"Forecasted revenue next 7 days: ₹{total_fc:,.0f}")
        waste = pred.get('waste', {}).get('estimated_loss_inr', 0)
        if waste:
            ctx_parts.append(f"Estimated food waste loss: ₹{waste:,.0f}")

    # Low stock items
    inv_list = list(col.inventory().find({'business_id': bid}, limit=200))
    if inv_list:
        low = [i.get('item_name', '') for i in inv_list
               if float(str(i.get('quantity', 99)).replace(',', '') or 99) <=
                  float(str(i.get('reorder_level', 0)).replace(',', '') or 0)]
        if low:
            ctx_parts.append(f"Low stock items: {', '.join(low[:5])}")

    return '. '.join(ctx_parts)


def _llm_anthropic(question: str, bid: str, biz_name: str, api_key: str) -> str:
    try:
        import anthropic
        ctx = _build_context(bid, biz_name)
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=512,
            system=(
                f"You are SmartServe AI, a concise business assistant for a food business. "
                f"Here is the current business data snapshot:\n{ctx}\n\n"
                "Answer the owner's question clearly and briefly. "
                "Only draw from the data provided — never invent numbers."
            ),
            messages=[{'role': 'user', 'content': question}],
        )
        return msg.content[0].text
    except Exception as e:
        return f"LLM error: {e}. Falling back to data summary. {_stats_answer(question, bid, biz_name)}"


def _llm_openai(question: str, bid: str, biz_name: str, api_key: str) -> str:
    try:
        from openai import OpenAI
        ctx = _build_context(bid, biz_name)
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model='gpt-4o-mini',
            max_tokens=512,
            messages=[
                {
                    'role': 'system',
                    'content': (
                        f"You are SmartServe AI, a concise business assistant. "
                        f"Business data snapshot:\n{ctx}\n"
                        "Answer briefly. Never invent numbers not in the data."
                    ),
                },
                {'role': 'user', 'content': question},
            ],
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"LLM error: {e}. {_stats_answer(question, bid, biz_name)}"


def _stats_answer(question: str, bid: str, biz_name: str) -> str:
    """Rule-based answerer using the business's real MongoDB data (no LLM configured)."""
    q = question.lower().strip()

    def has(*words):
        return any(w in q for w in words)

    # ── Greetings / thanks / help ─────────────────────────────────────────────
    if q in ('hi', 'hello', 'hey', 'yo') or has('good morning', 'good evening', 'good afternoon'):
        return f"Hi! I'm the SmartServe assistant for {biz_name}. Ask me about revenue, profit, orders, customers, your busiest day, top items, stock, forecasts, health score, or waste risk."
    if has('thank', 'thanks', 'thx'):
        return "You're welcome! Anything else you'd like to know about your business?"
    if has('what can you', 'help', 'how do you work', 'what do you do', 'options'):
        return ("I answer questions from your own data. Try things like:\n"
                "• \"What's my total revenue?\" / \"How much profit?\"\n"
                "• \"How many orders / customers do I have?\"\n"
                "• \"What's my busiest day?\" / \"Average order value?\"\n"
                "• \"What are my top items?\" / \"How is Cappuccino selling?\"\n"
                "• \"How's my stock?\" / \"What's my health score?\"\n"
                "• \"What's the sales forecast?\" / \"Any waste risk?\"")

    df = _load_sales_df(bid)
    has_sales = not df.empty and 'revenue' in df.columns
    pred = _latest_pred(bid)

    # ── Specific menu item lookup (e.g. "how is cappuccino selling") ──────────
    if has_sales:
        items = [str(i) for i in df['item_name'].dropna().unique()]
        matched = next((it for it in items if it and it.lower() in q), None)
        if matched and has('how', 'sell', 'selling', 'sold', 'doing', 'performance', 'revenue', 'much'):
            sub = df[df['item_name'] == matched]
            rev = sub['revenue'].sum()
            qty = sub['quantity'].sum() if 'quantity' in sub.columns else 0
            return f"\"{matched}\": ₹{rev:,.0f} total revenue from {int(qty):,} units sold across {len(sub)} sales records."

    # ── Profit / margin ───────────────────────────────────────────────────────
    if has('profit', 'margin'):
        if not has_sales:
            return "I don't see sales data yet. Upload your sales history (with a cost column) to see profit."
        rev = df['revenue'].sum()
        cost = df['cost'].sum() if 'cost' in df.columns else 0
        if cost == 0:
            return f"Total revenue is ₹{rev:,.0f}, but I don't have cost data, so I can't compute profit. Include a 'cost' column in your sales upload."
        profit = rev - cost
        margin = (profit / rev * 100) if rev else 0
        return f"Gross profit is ₹{profit:,.0f} on ₹{rev:,.0f} revenue — a {margin:.1f}% margin."

    # ── Average order / order value ───────────────────────────────────────────
    if has('average order', 'avg order', 'aov', 'average sale', 'per order', 'average transaction'):
        if not has_sales:
            return "No sales data yet — upload it to see your average order value."
        return f"Your average sale line-item value is ₹{df['revenue'].mean():,.0f} across {len(df):,} records."

    # ── Busiest day / peak ────────────────────────────────────────────────────
    if has('busiest', 'best day', 'peak', 'which day', 'busy day', 'slow day', 'worst day'):
        if not has_sales or '_date' not in df.columns or df['_date'].isna().all():
            return "I need dated sales data to find your busiest day. Upload sales with a date column."
        dow = df.dropna(subset=['_date']).groupby(df['_date'].dt.day_name())['revenue'].sum()
        order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
        dow = dow.reindex([d for d in order if d in dow.index])
        best, worst = dow.idxmax(), dow.idxmin()
        return f"Your busiest day is {best} (₹{dow.max():,.0f}) and the slowest is {worst} (₹{dow.min():,.0f}). See the Busiest Days chart in Analytics."

    # ── Orders count ──────────────────────────────────────────────────────────
    if has('how many order', 'order count', 'number of order', 'total order', 'orders do'):
        n = col.orders().count_documents({'business_id': bid})
        return (f"You have {n:,} orders recorded. See the Orders page for the full list."
                if n else "No orders recorded yet. Upload historical orders or create one from the Orders page.")

    # ── Customers ─────────────────────────────────────────────────────────────
    if has('customer', 'client', 'guest', 'loyal', 'regular'):
        custs = list(col.customers().find({'business_id': bid}))
        if not custs:
            return "No customer data yet. Upload a customers file or add them from the Customers page."
        top = sorted(custs, key=lambda c: float(c.get('total_spend', 0) or 0), reverse=True)[:3]
        names = ", ".join(f"{c.get('name','?')} (₹{float(c.get('total_spend',0) or 0):,.0f})" for c in top)
        return f"You have {len(custs):,} customers. Top spenders: {names}."

    # ── Forecast (checked before revenue so "sales forecast" isn't caught by it) ─
    if has('forecast', 'predict', 'next week', 'tomorrow', 'future', 'expect', 'projection'):
        if not pred:
            return "No forecast yet. Make sure you have 30+ days of sales data, then run the AI analysis."
        total_fc = pred.get('forecast', {}).get('total_forecast')
        if total_fc:
            return f"Your AI-forecasted revenue for the next 7 days is ₹{total_fc:,.0f}. See the forecast chart on the AI Results page."
        return "Forecast data exists — check the AI Results page for the 7-day chart."

    # ── Revenue / sales ───────────────────────────────────────────────────────
    if has('revenue', 'sales', 'earn', 'income', 'money', 'turnover', 'how much did i make'):
        if not has_sales:
            return "I don't see any sales data yet. Please upload your sales history first."
        total = df['revenue'].sum()
        msg = f"Your total recorded revenue is ₹{total:,.0f} across {len(df):,} sales records."
        if '_date' in df.columns and df['_date'].notna().any():
            latest = df['_date'].max()
            day_rev = df[df['_date'] == latest]['revenue'].sum()
            msg += f" Latest day ({latest.date()}): ₹{day_rev:,.0f}."
        return msg + " For period breakdowns, see the Analytics page."

    # ── Health score ──────────────────────────────────────────────────────────
    if has('health', 'score', 'performance', 'how am i doing', 'how is my business'):
        if not pred:
            return "No health score yet. Run the AI analysis from the AI Engine page first."
        hs = pred.get('health_score', {}).get('total_score')
        if hs is None:
            return "I couldn't read your health score. Try re-running the AI analysis."
        label = 'Excellent' if hs >= 80 else 'Good' if hs >= 60 else 'Fair' if hs >= 40 else 'Needs attention'
        comps = pred.get('health_score', {}).get('components', {})
        weakest = min(comps, key=comps.get) if comps else None
        extra = f" Weakest area: {weakest.replace('_',' ')}." if weakest else ""
        return f"Your business health score is {hs:.0f}/100 — {label}.{extra} Full breakdown on the AI Results page."

    # ── Menu / top / worst items ──────────────────────────────────────────────
    if has('menu', 'item', 'dish', 'best', 'popular', 'top', 'worst', 'star', 'seller', 'least'):
        wants_worst = has('worst', 'least', 'dog', 'bad', 'low perform')
        if pred:
            matrix = pred.get('profitability', {}).get('menu_matrix', {})
            bucket = matrix.get('Dogs') if wants_worst else matrix.get('Stars')
            if bucket:
                names = [s.get('item', '') for s in bucket[:4]]
                kind = "underperforming (Dogs — low popularity + low margin)" if wants_worst else "top (Stars — high popularity + high margin)"
                return f"Your {kind} items: {', '.join(names)}. See the full menu engineering matrix on the AI Results page."
        if has_sales:
            grp = df.groupby('item_name')['revenue'].sum()
            grp = grp.nsmallest(3) if wants_worst else grp.nlargest(3)
            label = "lowest" if wants_worst else "top"
            return f"{label.title()} 3 items by revenue: " + ", ".join(f"{i} (₹{v:,.0f})" for i, v in grp.items()) + "."
        return "Upload sales data (and run the AI analysis) to see menu performance."

    # ── Waste ─────────────────────────────────────────────────────────────────
    if has('waste', 'expiry', 'expire', 'spoil', 'loss', 'perish'):
        if pred:
            loss = pred.get('waste', {}).get('estimated_loss_inr', 0)
            items = pred.get('waste', {}).get('high_waste_items', [])
            names = ", ".join(w.get('item', '') for w in items[:3])
            extra = f" At-risk items: {names}." if names else ""
            return f"Estimated food waste loss: ₹{loss:,.0f}.{extra} See the AI Results page for details."
        return "Run the AI analysis to get waste risk estimates for your inventory."

    # ── Inventory / stock ─────────────────────────────────────────────────────
    if has('stock', 'inventory', 'ingredient', 'reorder', 'run out', 'low'):
        inv = list(col.inventory().find({'business_id': bid}, limit=300))
        if not inv:
            return "No inventory data found. Upload your inventory to get stock alerts."
        low = [i.get('item_name', '?') for i in inv
               if float(str(i.get('quantity', 99)).replace(',', '') or 99) <=
                  float(str(i.get('reorder_level', 0)).replace(',', '') or 0)]
        if low:
            return f"⚠️ {len(low)} item(s) at or below reorder level: {', '.join(low[:8])}. See the Inventory page."
        return f"Your inventory looks healthy — {len(inv)} items tracked, none below reorder level."

    # ── Staff ─────────────────────────────────────────────────────────────────
    if has('staff', 'employee', 'team', 'worker'):
        n = col.employees().count_documents({'business_id': bid})
        return (f"You have {n} staff member(s) on record. Manage them on the Staff page."
                if n else "No staff added yet. Add employees from the Staff page.")

    # ── Suppliers ─────────────────────────────────────────────────────────────
    if has('supplier', 'vendor', 'purchase order'):
        n = col.suppliers().count_documents({'business_id': bid})
        return (f"You have {n} supplier(s) on record. Manage them on the Suppliers page."
                if n else "No suppliers added yet. Add them from the Suppliers page.")

    # ── Default: give a quick data snapshot instead of a generic message ───────
    if has_sales:
        total = df['revenue'].sum()
        return (f"I'm not sure I caught that, but here's a quick snapshot for {biz_name}: "
                f"₹{total:,.0f} total revenue across {len(df):,} records. "
                "Ask me about profit, orders, customers, busiest day, top items, stock, forecast, health score, or waste.")
    return (
        f"I'm SmartServe AI for {biz_name}. I answer questions from your uploaded data — "
        "revenue, profit, orders, customers, stock, forecasts, health score, menu performance, and waste risk. "
        "Upload your data to get started, then ask away!"
    )
