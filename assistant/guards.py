"""
Security & policy guards for the assistant.

Responsibilities:
  • Tenant scoping — business_id is ALWAYS injected server-side and applied at
    the query layer. The LLM/user can never supply or override it.
  • Role checks — Staff never receive owner-level financial answers. Enforced
    here (and called inside tool functions), never left to the prompt.
  • Prompt-injection defense — user chat text is untrusted *data*, not
    instructions. Attempts to change rules / exfiltrate other tenants' data /
    reveal the system prompt are detected and logged.
  • Feedback logging — unanswered / low-confidence questions and security
    events are recorded (best-effort; logging never breaks a response).

Pure-logic functions here are import-safe and DB-free so they can be unit
tested without MongoDB or an LLM key.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone


class TenantViolation(Exception):
    """Raised when code attempts to query without / across the wrong business_id."""


# ── Roles ────────────────────────────────────────────────────────────────────
ROLE_RANK = {'staff': 1, 'manager': 2, 'owner': 3}

# Financial answers Staff must not receive. Enforced at the function layer.
FINANCIAL_METRICS = {'profit', 'margin', 'cost'}
FINANCIAL_INTENTS = {'profitability', 'recommendation'}
# Minimum role required for financial answers.
FINANCIAL_MIN_RANK = ROLE_RANK['manager']


def role_rank(role: str | None) -> int:
    return ROLE_RANK.get((role or '').lower(), ROLE_RANK['staff'])


def is_financial(intent: str | None = None, metric: str | None = None) -> bool:
    return (intent in FINANCIAL_INTENTS) or (metric in FINANCIAL_METRICS)


def check_access(role: str | None, intent: str | None = None, metric: str | None = None):
    """
    Return (allowed: bool, reason: str|None). `reason` is a user-facing message
    when access is denied.
    """
    if is_financial(intent, metric) and role_rank(role) < FINANCIAL_MIN_RANK:
        return False, (
            "That's an owner/manager-level financial figure, and your account is a "
            "Staff account. Ask your manager for revenue, profit, or margin details."
        )
    return True, None


# ── Tenant scoping ───────────────────────────────────────────────────────────
def assert_business_id(business_id) -> str:
    """Guarantee a non-empty business_id is present before any query runs."""
    if not business_id or not str(business_id).strip():
        raise TenantViolation("No business_id in session — refusing to run a query.")
    return str(business_id)


def scoped_query(business_id, extra: dict | None = None) -> dict:
    """
    Build a Mongo filter that is ALWAYS pinned to this business_id. Any attempt
    (via `extra`) to set/override business_id is a tenant violation and is
    rejected — the model can never widen the scope.
    """
    bid = assert_business_id(business_id)
    q = dict(extra or {})
    if 'business_id' in q and str(q['business_id']) != bid:
        raise TenantViolation(
            f"Attempt to query business_id={q['business_id']!r} under session {bid!r}."
        )
    q['business_id'] = bid
    return q


# ── Prompt-injection detection ───────────────────────────────────────────────
# Patterns that indicate the user is trying to steer the *system* rather than
# ask about their business. Matches are treated as untrusted and logged.
_INJECTION_PATTERNS = [
    r"\bignore (all|any|the|your|previous|prior|above)\b",
    r"\bdisregard (all|any|the|your|previous|prior|above)\b",
    r"\b(system|developer)\s*(prompt|message|instruction)",
    r"\breveal|show me your (system )?(prompt|instructions|rules)\b",
    r"\byou are now\b|\bpretend (to be|you are)\b|\bact as\b",
    r"\bforget (everything|all|your) (instructions|rules)\b",
    r"\boverride (the |your )?(rules|instructions|business|tenant)",
    r"\b(other|another|different|all) (business|businesses|tenant|company)('s)?\b",
    r"\bbusiness[_ ]?id\b",
    r"\bchange (the |your )?rules\b",
    r"\bjailbreak\b|\bDAN\b",
]
_INJECTION_RE = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def detect_injection(text: str):
    """
    Return (is_suspicious: bool, matched: str|None). This does not block the
    user — it flags the message so the orchestrator can refuse instruction-like
    requests and log the attempt, while still treating the text as data.
    """
    t = text or ''
    for rx in _INJECTION_RE:
        m = rx.search(t)
        if m:
            return True, m.group(0)
    return False, None


# ── Best-effort logging (never breaks a response) ────────────────────────────
def _logging_disabled() -> bool:
    try:
        from django.conf import settings
        return bool(getattr(settings, 'TESTING', False))
    except Exception:
        return False


def log_gap(business_id, user_id, question: str, intent: str | None, reason: str) -> None:
    """Record an unanswered / low-confidence question for coverage improvement."""
    if _logging_disabled():
        return
    try:
        from mongo import collections as col
        col.get_db()['assistant_gaps'].insert_one({
            'business_id': assert_business_id(business_id),
            'user_id': str(user_id) if user_id is not None else None,
            'question': (question or '')[:1000],
            'intent': intent,
            'reason': reason,
            'created_at': datetime.now(timezone.utc),
        })
    except Exception:
        pass  # logging must never break the reply


def log_security_event(business_id, user_id, question: str, kind: str, detail: str = '') -> None:
    """Record a prompt-injection / policy event to the audit log."""
    if _logging_disabled():
        return
    try:
        from mongo import collections as col
        col.audit_logs().insert_one({
            'business_id': str(business_id) if business_id else None,
            'user_id': str(user_id) if user_id is not None else None,
            'source': 'assistant',
            'kind': kind,
            'detail': (detail or '')[:500],
            'question': (question or '')[:1000],
            'created_at': datetime.now(timezone.utc),
        })
    except Exception:
        pass
