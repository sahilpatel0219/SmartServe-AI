"""
Conversation memory for follow-ups.

Keeps the last few turns per (business, user) so "what about last month?",
"and pizza?", or "why?" resolve against the previous question's intent and
entities. Capped and scoped; stored in Django's cache (falls back to a safe
no-op if unavailable).
"""
from __future__ import annotations

import re
from datetime import date

MAX_TURNS = 5
TTL_SECONDS = 30 * 60

_FOLLOWUP_RE = re.compile(
    r'^\s*(and|what about|how about|ok(ay)? and|also|then)\b'
    r'|^\s*why\??\s*$|^\s*(and )?(what|how) about\b', re.IGNORECASE)


def _key(business_id, user_id) -> str:
    return f'assistant_ctx:{business_id}:{user_id}'


def _cache():
    try:
        from django.core.cache import cache
        return cache
    except Exception:
        return None


def load(business_id, user_id) -> list[dict]:
    c = _cache()
    if not c:
        return []
    return c.get(_key(business_id, user_id)) or []


def save_turn(business_id, user_id, question: str, intent: str, ent_snapshot: dict) -> None:
    c = _cache()
    if not c:
        return
    turns = load(business_id, user_id)
    turns.append({'q': question, 'intent': intent, 'ent': ent_snapshot})
    c.set(_key(business_id, user_id), turns[-MAX_TURNS:], TTL_SECONDS)


def clear(business_id, user_id) -> None:
    c = _cache()
    if c:
        c.delete(_key(business_id, user_id))


def snapshot(ent: dict) -> dict:
    """Serialize entities for storage (dates → ISO)."""
    tr = ent.get('time_range')
    return {
        'metric': ent.get('metric'),
        'item': (ent.get('item') or {}).get('match'),
        'category': ent.get('category'),
        'segment': ent.get('segment'),
        'time_range': ({'start': tr['start'].isoformat(), 'end': tr['end'].isoformat(),
                        'label': tr['label']} if tr else None),
    }


def is_followup(text: str) -> bool:
    return bool(_FOLLOWUP_RE.search(text or ''))


def restore(prev_snap: dict) -> dict:
    """Rebuild an entities dict from a stored snapshot (ISO → dates)."""
    tr = prev_snap.get('time_range')
    time_range = None
    if tr:
        time_range = {'start': date.fromisoformat(tr['start']), 'end': date.fromisoformat(tr['end']),
                      'label': tr['label']}
    return {
        'metric': prev_snap.get('metric'),
        'time_range': time_range,
        'item': {'match': prev_snap.get('item'), 'ambiguous': False, 'candidates': [], 'score': 1.0},
        'category': prev_snap.get('category'),
        'segment': prev_snap.get('segment'),
        'is_comparison': False,
    }


def merge(prev_turn: dict, new_ent: dict, text: str) -> tuple[str, dict]:
    """
    Merge a follow-up into the previous turn: inherit intent + entities, then
    overlay anything explicitly present in the follow-up. "why" switches to a
    diagnostic on the previous window.
    """
    base = restore(prev_turn.get('ent', {}))
    # overlay explicitly-present entities from the new short question
    if new_ent.get('metric'):
        base['metric'] = new_ent['metric']
    if new_ent.get('time_range'):
        base['time_range'] = new_ent['time_range']
    if (new_ent.get('item') or {}).get('match'):
        base['item'] = new_ent['item']
    if new_ent.get('category'):
        base['category'] = new_ent['category']
    if new_ent.get('segment'):
        base['segment'] = new_ent['segment']

    intent = prev_turn.get('intent', 'metric_lookup')
    if re.search(r'\bwhy\b', text or '', re.IGNORECASE):
        intent = 'diagnostic'
    return intent, base
