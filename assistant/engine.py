"""
Engine — picks the answering mode, applies cost/abuse controls, and manages
conversation memory. Guarantees a reply.

  • Fallback mode (no LLM key): the rules-based orchestrator answers directly.
  • LLM mode (key set): the model does understanding + phrasing over the SAME
    deterministic tool layer; any failure degrades to the fallback orchestrator.

Cross-cutting here: per-user rate limiting, a brief identical-query cache (to
cut latency/API cost), and loading/saving the last few conversation turns so
follow-ups resolve.
"""
from __future__ import annotations

import hashlib

from django.conf import settings

from assistant import orchestrator, context as ctx

RATE_LIMIT_PER_MIN = getattr(settings, 'ASSISTANT_RATE_LIMIT_PER_MIN', 40)
QUERY_CACHE_SECONDS = 8


def _llm_configured() -> bool:
    return bool(getattr(settings, 'LLM_PROVIDER', '') and getattr(settings, 'LLM_API_KEY', ''))


def _cache():
    try:
        from django.core.cache import cache
        return cache
    except Exception:
        return None


def _rate_limited(cache, business_id, user_id) -> bool:
    if not cache:
        return False
    key = f'assistant_rl:{business_id}:{user_id}'
    n = cache.get(key, 0)
    if n >= RATE_LIMIT_PER_MIN:
        return True
    cache.set(key, n + 1, 60)
    return False


def _qkey(business_id, user_id, question) -> str:
    h = hashlib.md5((question or '').lower().strip().encode('utf-8')).hexdigest()
    return f'assistant_q:{business_id}:{user_id}:{h}'


def respond(question: str, business_id, role: str, biz_name: str, user_id=None) -> dict:
    cache = _cache()

    if _rate_limited(cache, business_id, user_id):
        return {'reply': "You're asking a lot very quickly — give me a few seconds and try again.",
                'intent': 'rate_limited', 'ok': False, 'chips': [], 'needs_clarification': False}

    is_fu = ctx.is_followup(question)
    # Brief identical-query cache (skipped for follow-ups, which depend on context).
    if cache and not is_fu:
        hit = cache.get(_qkey(business_id, user_id, question))
        if hit:
            return hit

    conv = ctx.load(business_id, user_id)

    result = None
    if _llm_configured():
        try:
            from assistant.llm import answer_with_llm
            result = answer_with_llm(question, business_id, role, biz_name, user_id=user_id)
        except Exception:
            result = None
    if result is None:
        result = orchestrator.answer(question, business_id, role, biz_name,
                                     user_id=user_id, context=conv)

    # Remember this turn (for follow-ups), then drop the internal snapshot.
    ent_snap = result.pop('_ent', None)
    if result.get('ok') and result.get('intent') not in ('greeting', 'out_of_scope', 'unclear', 'rate_limited'):
        ctx.save_turn(business_id, user_id, question, result.get('intent', ''), ent_snap or {})

    if cache and not is_fu and result.get('ok'):
        cache.set(_qkey(business_id, user_id, question), result, QUERY_CACHE_SECONDS)
    return result
