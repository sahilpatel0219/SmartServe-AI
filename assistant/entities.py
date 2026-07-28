"""
Entity extraction & normalization for the assistant.

Turns naturally phrased questions into concrete, query-ready entities:
  • time ranges  → concrete (start_date, end_date) with a human label
  • metrics      → canonical names (revenue, orders, quantity, profit, ...)
  • menu items   → fuzzy-matched against THIS business's real catalog
  • categories   → matched against the business's categories
  • segments     → vip / regular / inactive
  • comparisons  → the "vs X" target when present

Everything is normalized to dates / canonical strings BEFORE any query runs.
Pure logic, no DB and no LLM — fully unit-testable. Fuzzy matching uses the
stdlib `difflib` (no extra dependency).
"""
from __future__ import annotations

import re
import calendar
import difflib
from datetime import date, timedelta

try:
    from dateutil.relativedelta import relativedelta
except Exception:  # pragma: no cover - dateutil ships with pandas
    relativedelta = None


# ── Metrics ──────────────────────────────────────────────────────────────────
_METRIC_KEYWORDS = {
    'revenue':  ['revenue', 'sales', 'turnover', 'income', 'earn', 'earning', 'made', 'make', 'money', 'takings'],
    'profit':   ['profit', 'earnings', 'net'],
    'margin':   ['margin', 'markup'],
    'cost':     ['cost', 'cogs', 'expense', 'spend'],
    'orders':   ['order', 'orders', 'transaction', 'transactions', 'bills', 'covers', 'tickets'],
    'quantity': ['quantity', 'units', 'qty', 'volume', 'how many sold', 'pieces', 'plates'],
    'waste':    ['waste', 'wastage', 'wasting', 'wasted', 'spoil', 'spoilage', 'expiry', 'expire'],
    'footfall': ['footfall', 'customers', 'visitors', 'guests', 'traffic'],
}
# Priority order when several match (profit/margin are more specific than revenue).
_METRIC_PRIORITY = ['margin', 'profit', 'cost', 'waste', 'quantity', 'orders', 'footfall', 'revenue']


def extract_metric(text: str, default: str | None = None) -> str | None:
    t = f' {(text or "").lower()} '
    found = set()
    for metric, kws in _METRIC_KEYWORDS.items():
        for kw in kws:
            if f' {kw} ' in t or (kw in t and ' ' not in kw):
                found.add(metric)
                break
    for m in _METRIC_PRIORITY:
        if m in found:
            return m
    return default


# ── Segments ─────────────────────────────────────────────────────────────────
def extract_segment(text: str) -> str | None:
    t = (text or '').lower()
    if 'vip' in t or 'top spender' in t or 'best customer' in t:
        return 'VIP'
    if 'regular' in t or 'repeat' in t or 'loyal' in t:
        return 'Regular'
    if 'inactive' in t or 'lapsed' in t or 'lost customer' in t or 'churn' in t:
        return 'Inactive'
    return None


# ── Categories ───────────────────────────────────────────────────────────────
def extract_category(text: str, categories: list[str] | None) -> str | None:
    if not categories:
        return None
    t = (text or '').lower()
    for cat in categories:
        if cat and cat.lower() in t:
            return cat
    # a couple of common colloquialisms
    aliases = {'drinks': ['beverage', 'beverages', 'drink'], 'food': ['mains', 'main']}
    for cat in categories:
        cl = (cat or '').lower()
        for canon, al in aliases.items():
            if cl == canon and any(a in t for a in al):
                return cat
    return None


# ── Comparison target ────────────────────────────────────────────────────────
def extract_comparison(text: str) -> bool:
    t = (text or '').lower()
    return bool(re.search(r'\b(vs|versus|compared? to|compare|against|better than|worse than|difference between)\b', t))


# ── Fuzzy item matching ──────────────────────────────────────────────────────
_ITEM_SYNONYMS = {'iced': 'cold', 'ice': 'cold', 'chilled': 'cold', 'veggie': 'veg'}


def _norm(s: str) -> str:
    s = (s or '').lower()
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def _tokens(s: str) -> list[str]:
    return [_ITEM_SYNONYMS.get(tok, tok) for tok in _norm(s).split()]


def match_item(text: str, catalog: list[str] | None, threshold: float = 0.6) -> dict:
    """
    Fuzzy-match a menu item mentioned in `text` against the business's catalog.

    Returns { 'match': name|None, 'score': float, 'ambiguous': bool,
              'candidates': [names] }.
    "cold coffee" / "Cold Coffee" / "iced coffee" / "coffee cold" all resolve to
    the real "Cold Coffee". If two items match closely, `ambiguous` is set and
    the caller should ask which one.
    """
    empty = {'match': None, 'score': 0.0, 'ambiguous': False, 'candidates': []}
    if not catalog:
        return empty
    q = _tokens(text)
    if not q:
        return empty
    qset = set(q)

    scored: list[tuple[float, str]] = []
    for name in catalog:
        it = _tokens(name)
        if not it:
            continue
        itset = set(it)
        # containment: fraction of item tokens present in the query (fuzzy per token)
        found = 0.0
        for tok in it:
            if tok in qset:
                found += 1
            elif any(difflib.SequenceMatcher(None, tok, qt).ratio() >= 0.82 for qt in q):
                found += 0.9
        contain = found / len(it)
        # whole-string similarity (order-independent) as a secondary signal
        seq = difflib.SequenceMatcher(None, ' '.join(sorted(itset)), ' '.join(sorted(qset))).ratio()
        score = max(contain, seq * 0.9)
        scored.append((round(score, 4), name))

    if not scored:
        return empty
    scored.sort(reverse=True)
    strong = [name for sc, name in scored if sc >= threshold]

    # two strong, near-tied matches → ambiguous
    if len(strong) >= 2 and (scored[0][0] - scored[1][0]) < 0.12:
        return {'match': None, 'score': scored[0][0], 'ambiguous': True, 'candidates': strong[:3]}
    if scored[0][0] >= threshold:
        return {'match': scored[0][1], 'score': scored[0][0], 'ambiguous': False, 'candidates': [scored[0][1]]}

    # nothing confident, but offer near-misses for clarification
    near = [name for sc, name in scored if sc >= 0.45][:3]
    return {'match': None, 'score': scored[0][0], 'ambiguous': len(near) > 1, 'candidates': near}


# ── Time ranges ──────────────────────────────────────────────────────────────
_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
_MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})


def _fmt_label(start: date, end: date) -> str:
    if start == end:
        return start.strftime('%-d %b %Y') if _supports_dash() else start.strftime('%d %b %Y').lstrip('0')
    if start.year == end.year and start.month == end.month:
        return f"{start.day}–{end.day} {end.strftime('%b %Y')}"
    if start.year == end.year:
        return f"{start.strftime('%d %b').lstrip('0')} – {end.strftime('%d %b %Y').lstrip('0')}"
    return f"{start.strftime('%d %b %Y').lstrip('0')} – {end.strftime('%d %b %Y').lstrip('0')}"


def _supports_dash() -> bool:
    try:
        date(2020, 1, 5).strftime('%-d')
        return True
    except Exception:
        return False


def range_label(start: date, end: date) -> str:
    """Public helper — human label for an inclusive [start, end] range."""
    return _fmt_label(start, end)


def _month_range(year: int, month: int) -> tuple[date, date]:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def resolve_time_range(text: str, today: date | None = None) -> dict | None:
    """
    Resolve relative time language to a concrete inclusive [start, end] range.
    Returns { 'start': date, 'end': date, 'label': str, 'granularity': str } or
    None if no time expression is present (caller applies a default window).
    """
    t = (text or '').lower()
    today = today or date.today()

    def result(start: date, end: date, gran: str = 'day') -> dict:
        return {'start': start, 'end': end, 'label': _fmt_label(start, end), 'granularity': gran}

    # today / yesterday
    if re.search(r'\btoday\b', t):
        return result(today, today)
    if re.search(r'\byesterday\b', t):
        y = today - timedelta(days=1)
        return result(y, y)

    # "past/last N days" / "last N weeks/months"
    m = re.search(r'\b(?:past|last|previous)\s+(\d{1,3})\s+day', t)
    if m:
        n = int(m.group(1))
        return result(today - timedelta(days=n - 1), today)
    m = re.search(r'\b(?:past|last|previous)\s+(\d{1,3})\s+week', t)
    if m:
        n = int(m.group(1))
        return result(today - timedelta(days=n * 7 - 1), today, 'week')
    m = re.search(r'\b(?:past|last|previous)\s+(\d{1,3})\s+month', t)
    if m and relativedelta:
        n = int(m.group(1))
        return result((today - relativedelta(months=n)) + timedelta(days=1), today, 'month')

    # this / last week (Mon–Sun)
    monday = today - timedelta(days=today.weekday())
    if re.search(r'\blast week\b', t):
        lm = monday - timedelta(days=7)
        return result(lm, lm + timedelta(days=6), 'week')
    if re.search(r'\bthis week\b', t):
        return result(monday, today, 'week')

    # weekend
    saturday = monday + timedelta(days=5)
    if re.search(r'\blast weekend\b', t):
        ls = saturday - timedelta(days=7)
        return result(ls, ls + timedelta(days=1), 'day')
    if re.search(r'\b(this )?weekend\b', t):
        return result(saturday, saturday + timedelta(days=1), 'day')

    # this / last month
    if re.search(r'\blast month\b', t) and relativedelta:
        prev = today - relativedelta(months=1)
        return result(*_month_range(prev.year, prev.month), gran='month')
    if re.search(r'\bthis month\b', t):
        return result(today.replace(day=1), today, 'month')

    # quarter
    if re.search(r'\b(this )?quarter\b', t) or re.search(r'\blast quarter\b', t):
        q = (today.month - 1) // 3
        q_start_month = q * 3 + 1
        if 'last' in t and relativedelta:
            start = date(today.year, q_start_month, 1) - relativedelta(months=3)
            end = date(today.year, q_start_month, 1) - timedelta(days=1)
            return result(start, end, 'month')
        return result(date(today.year, q_start_month, 1), today, 'month')

    # this / last year
    if re.search(r'\blast year\b', t):
        return result(date(today.year - 1, 1, 1), date(today.year - 1, 12, 31), 'month')
    if re.search(r'\bthis year\b', t):
        return result(date(today.year, 1, 1), today, 'month')

    # "since <month> [year]"
    m = re.search(r'\bsince\s+([a-z]+)(?:\s+(\d{4}))?', t)
    if m and m.group(1) in _MONTHS:
        mon = _MONTHS[m.group(1)]
        yr = int(m.group(2)) if m.group(2) else today.year
        if not m.group(2) and mon > today.month:  # "since December" but it's June → last year
            yr -= 1
        start = date(yr, mon, 1)
        if start <= today:
            return result(start, today, 'month')

    # "in <month> [year]"
    m = re.search(r'\b(?:in|during|for)\s+([a-z]+)(?:\s+(\d{4}))?', t)
    if m and m.group(1) in _MONTHS:
        mon = _MONTHS[m.group(1)]
        yr = int(m.group(2)) if m.group(2) else today.year
        if not m.group(2) and mon > today.month:
            yr -= 1
        return result(*_month_range(yr, mon), gran='month')

    return None


def default_window(today: date | None = None, days: int = 7) -> dict:
    """A sensible recent window used when the question names no time range."""
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    return {'start': start, 'end': today, 'label': _fmt_label(start, today), 'granularity': 'day'}


# ── Bundle ───────────────────────────────────────────────────────────────────
def extract_entities(text: str, catalog: list[str] | None = None,
                     categories: list[str] | None = None, today: date | None = None) -> dict:
    """Extract every entity type from a question in one pass."""
    return {
        'metric': extract_metric(text),
        'time_range': resolve_time_range(text, today=today),
        'item': match_item(text, catalog),
        'category': extract_category(text, categories),
        'segment': extract_segment(text),
        'is_comparison': extract_comparison(text),
    }
