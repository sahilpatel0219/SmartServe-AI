"""
AI Assistant views.

The chat endpoint routes every question through the engine (rate-limit +
identical-query cache + conversation memory) into the orchestrator (intent →
entities → deterministic tools → composed answer). Works with and without an
LLM key. A feedback endpoint stores thumbs up/down and feeds the gap log.
"""
import json
from datetime import datetime, timezone

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings

from mongo import collections as col


def _get_business(request):
    from core.utils import get_active_business
    return get_active_business(request)


def _starter_chips(business_id) -> list[str]:
    """Suggestion chips generated from what data the business actually has."""
    from assistant.tools import functions as afn
    try:
        avail = afn.get_data_availability(business_id)
    except Exception:
        avail = {}
    chips = []
    if avail.get('has_sales'):
        chips += ["What's my revenue this week?", "What are my best sellers?", "How does this week compare to last week?"]
    if avail.get('has_analysis'):
        chips.append("What's my health score?")
    if avail.get('has_inventory'):
        chips.append("What should I reorder?")
    if avail.get('has_customers'):
        chips.append("Who are my top customers?")
    return chips[:6] or ["Upload your sales data, then ask me anything about it"]


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
        'starter_chips': _starter_chips(bid),
        'llm_enabled': bool(getattr(settings, 'LLM_PROVIDER', '') and getattr(settings, 'LLM_API_KEY', '')),
    })


@login_required
@require_POST
def chat_view(request):
    business, membership = _get_business(request)
    if not business:
        return JsonResponse({'error': 'No active business'}, status=403)
    role = getattr(membership, 'role', 'staff') or 'staff'

    try:
        body = json.loads(request.body)
        question = str(body.get('message', '')).strip()
    except Exception:
        return JsonResponse({'error': 'Invalid request'}, status=400)
    if not question:
        return JsonResponse({'error': 'Empty message'}, status=400)

    from assistant.engine import respond
    result = respond(question, business.mongo_id, role, business.name, user_id=request.user.id)
    return JsonResponse({
        'reply': result.get('reply', ''),
        'chips': result.get('chips', []),
        'intent': result.get('intent'),
        'needs_clarification': result.get('needs_clarification', False),
    })


@login_required
@require_POST
def feedback_view(request):
    """Store a thumbs up/down on an answer; thumbs-down also feeds the gap log."""
    business, _ = _get_business(request)
    if not business:
        return JsonResponse({'error': 'No active business'}, status=403)
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid request'}, status=400)
    rating = body.get('rating')
    if rating not in ('up', 'down'):
        return JsonResponse({'error': 'Invalid rating'}, status=400)

    question = str(body.get('question', ''))[:1000]
    answer = str(body.get('answer', ''))[:2000]
    try:
        col.get_db()['assistant_feedback'].insert_one({
            'business_id': business.mongo_id, 'user_id': request.user.id,
            'question': question, 'answer': answer, 'rating': rating,
            'created_at': datetime.now(timezone.utc),
        })
    except Exception:
        pass
    if rating == 'down':
        from assistant.guards import log_gap
        log_gap(business.mongo_id, request.user.id, question, 'thumbs_down', 'user_flagged_unhelpful')
    return JsonResponse({'ok': True})
