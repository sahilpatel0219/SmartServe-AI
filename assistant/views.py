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
    m = Membership.objects.filter(user=request.user, is_active=True).select_related('business').first()
    return (m.business, m) if m else (None, None)


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


def _build_context(bid: str, biz_name: str) -> str:
    """Summarise key business metrics from MongoDB for LLM context."""
    import pandas as pd

    ctx_parts = [f"Business: {biz_name}"]

    # Recent sales summary
    records = list(col.sales_records().find({'business_id': bid}, limit=500))
    if records:
        df = pd.DataFrame(records)
        rev_col = next((c for c in ['revenue', 'amount'] if c in df.columns), None)
        if rev_col:
            df['_rev'] = pd.to_numeric(df[rev_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            ctx_parts.append(f"Total sales records: {len(df)}")
            ctx_parts.append(f"Total revenue in dataset: ₹{df['_rev'].sum():,.0f}")
            ctx_parts.append(f"Average transaction: ₹{df['_rev'].mean():,.0f}")

    # Latest prediction
    pred = col.predictions().find_one({'business_id': bid}, sort=[('created_at', -1)])
    if pred:
        hs = pred.get('health_score', {}).get('total_score', None)
        if hs is not None:
            ctx_parts.append(f"Business health score: {hs:.1f}/100")
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
    """Rule-based answerer using real MongoDB data when no LLM is configured."""
    import pandas as pd
    q = question.lower()

    # Revenue / sales questions
    if any(w in q for w in ['revenue', 'sales', 'earn', 'income', 'money']):
        records = list(col.sales_records().find({'business_id': bid}, limit=1000))
        if not records:
            return "I don't see any sales data yet. Please upload your sales history first."
        df = pd.DataFrame(records)
        rev_col = next((c for c in ['revenue', 'amount'] if c in df.columns), None)
        if rev_col:
            total = pd.to_numeric(df[rev_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum()
            return f"Based on your uploaded data ({len(df)} records), your total recorded revenue is ₹{total:,.0f}. For period-specific breakdowns, check the Analytics page."
        return "Sales data found but revenue column not recognized. Try re-uploading with a 'revenue' column."

    # Inventory / stock questions
    if any(w in q for w in ['stock', 'inventory', 'ingredient', 'low', 'reorder']):
        inv = list(col.inventory().find({'business_id': bid}, limit=200))
        if not inv:
            return "No inventory data found. Upload your inventory to get stock alerts."
        low = [i.get('item_name', '?') for i in inv
               if float(str(i.get('quantity', 99)).replace(',', '') or 99) <=
                  float(str(i.get('reorder_level', 0)).replace(',', '') or 0)]
        if low:
            return f"⚠️ {len(low)} item(s) are at or below reorder level: {', '.join(low[:8])}. Check the Inventory page for details."
        return f"Your inventory looks healthy — {len(inv)} items tracked, none below reorder level."

    # Health score
    if any(w in q for w in ['health', 'score', 'performance']):
        pred = col.predictions().find_one({'business_id': bid}, sort=[('created_at', -1)])
        if not pred:
            return "No health score yet. Run the AI analysis first from the AI Analysis page."
        hs = pred.get('health_score', {}).get('total_score', None)
        if hs is not None:
            label = 'Excellent' if hs >= 80 else 'Good' if hs >= 60 else 'Fair' if hs >= 40 else 'Needs attention'
            return f"Your latest business health score is {hs:.1f}/100 — {label}. Check the AI Analysis page for a full breakdown."

    # Forecast / prediction
    if any(w in q for w in ['forecast', 'predict', 'next week', 'tomorrow', 'future']):
        pred = col.predictions().find_one({'business_id': bid}, sort=[('created_at', -1)])
        if not pred:
            return "No forecast available yet. Upload at least 30 days of sales data and run the AI analysis."
        summary = pred.get('forecast_summary', {})
        total7 = summary.get('next_7_days_total', None)
        if total7:
            return f"Your AI-forecasted revenue for the next 7 days is ₹{total7:,.0f}. See the full forecast on the AI Results page."
        return "Forecast data exists. Check the AI Results page for the 7-day forecast chart."

    # Menu / items
    if any(w in q for w in ['menu', 'item', 'dish', 'best', 'popular', 'top']):
        pred = col.predictions().find_one({'business_id': bid}, sort=[('created_at', -1)])
        if pred:
            stars = pred.get('profitability', {}).get('menu_matrix', {}).get('Stars', [])
            if stars:
                names = [s.get('item', '') for s in stars[:3]]
                return f"Your top-performing menu items (Stars — high popularity + high margin): {', '.join(names)}. See the full menu engineering matrix on the AI Results page."
        records = list(col.sales_records().find({'business_id': bid}, limit=500))
        if records:
            import pandas as pd
            df = pd.DataFrame(records)
            item_col = next((c for c in ['item_name', 'item'] if c in df.columns), None)
            rev_col = next((c for c in ['revenue', 'amount'] if c in df.columns), None)
            if item_col and rev_col:
                df['_rev'] = pd.to_numeric(df[rev_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                top = df.groupby(item_col)['_rev'].sum().nlargest(3).index.tolist()
                return f"Top 3 items by revenue from your sales data: {', '.join(top)}."
        return "Upload sales data and run the AI analysis to see menu performance."

    # Waste
    if any(w in q for w in ['waste', 'expiry', 'expire', 'spoil', 'loss']):
        pred = col.predictions().find_one({'business_id': bid}, sort=[('created_at', -1)])
        if pred:
            loss = pred.get('waste', {}).get('estimated_loss_inr', 0)
            return f"Estimated food waste loss based on your data: ₹{loss:,.0f}. Check the AI Results page for items at highest risk."
        return "Run the AI analysis to get waste risk estimates for your inventory."

    # Default
    return (
        f"I'm SmartServe AI for {biz_name}. I can answer questions about your revenue, "
        "inventory stock levels, AI forecasts, health score, menu performance, and waste risk — "
        "all from your uploaded data. What would you like to know?"
    )
