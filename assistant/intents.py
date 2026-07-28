"""
Intent taxonomy + classifier for the assistant.

Classifies a question into one or more intents via keyword/pattern sets. This
is the fallback-mode classifier and also a strong prior the LLM path can lean
on. Intents can combine (e.g. "why were pizza sales down last week" =
diagnostic + metric period), so `classify` returns an ordered list plus the
primary intent.

Pure logic — no DB, no LLM.
"""
from __future__ import annotations

import re

INTENTS = [
    'metric_lookup', 'comparison', 'ranking', 'trend', 'diagnostic', 'forecast',
    'inventory', 'profitability', 'waste', 'customer', 'staffing',
    'recommendation', 'explanation', 'greeting', 'out_of_scope', 'unclear',
]

# Each intent maps to a list of regex patterns. A match scores 1 (weighted).
_PATTERNS: dict[str, list[str]] = {
    'diagnostic': [
        r'\bwhy\b', r'\bwhat (caused|happened)\b', r'\breason (for|behind)\b',
        r'\bexplain why\b', r'\bhow come\b',
    ],
    'forecast': [
        r'\bforecast\b', r'\bpredict', r'\bexpect(ed|ing)?\b', r'\bprojection\b',
        r'\bnext (week|month|day|weekend|few days)\b', r'\btomorrow\b',
        r'\bwill (i|we|it|sell|make|sales)\b', r'\bgoing to (sell|make)\b', r'\bupcoming\b',
    ],
    'comparison': [
        r'\bvs\b', r'\bversus\b', r'\bcompared? to\b', r'\bcompare\b', r'\bagainst\b',
        r'\bbetter than\b', r'\bworse than\b', r'\bdifference between\b',
        r'\b(this|last) \w+ (vs|versus|compared)\b',
    ],
    'ranking': [
        r'\bbest[- ]?sell', r'\btop (item|seller|selling|product|dish)', r'\bworst\b',
        r'\bleast (popular|selling|profitable)\b', r'\bmost (popular|sold|profitable|wasteful)\b',
        r'\bhighest\b', r'\blowest\b', r'\brank(ing)?\b', r'\bbestseller', r'\bpopular\b',
    ],
    'trend': [
        r'\btrend', r'\bgrowing\b', r'\bdeclin', r'\brising\b', r'\bfalling\b',
        r'\bover time\b', r'\bmoved?\b', r'\bmoving\b', r'\bhow (have|has) .* (change|move|grow)',
        r'\bsince \w+', r'\bweek over week\b', r'\bmonth over month\b',
    ],
    'inventory': [
        r'\bstock\b', r'\binventory\b', r'\breorder\b', r'\brun(ning)? (out|low)\b',
        r'\blow stock\b', r'\bwhat should i (buy|order|reorder)\b', r'\bexpir(e|es|ing|y)\b',
        r'\brestock\b', r'\bingredient', r'\bshould i (buy|order)\b',
    ],
    'waste': [
        r'\bwast\w*', r'\bspoil\w*', r'\bthrow(ing)? (away|out)\b',
        r'\bgoing bad\b', r'\bperish\w*', r'\bexpire before\b',
    ],
    'profitability': [
        r'\bmargin\b', r'\bmost (money|profit)\b', r'\bmake the most\b', r'\bmost profitable\b',
        r'\bleast profitable\b', r'\braise (the )?price', r'\bpricing\b', r'\bshould i (raise|change) (any )?price',
        r'\bwhich items? (make|earn)\b',
    ],
    'customer': [
        r'\bcustomer', r'\bregulars?\b', r'\brepeat\b', r'\bloyal', r'\bvip\b',
        r'\bwho (are|is) my\b', r'\bhow many (repeat|regular|new) customer',
    ],
    'staffing': [
        r'\bstaff', r'\bemployee', r'\bwhen am i busiest\b', r'\bpeak (time|hour)',
        r'\bbusiest (time|hour|day)\b', r'\bhow many (staff|people|servers)\b',
        r'\bwhen do i need\b', r'\brush hour', r'\bshift', r'\bfootfall\b',
    ],
    'recommendation': [
        r'\bwhat should i do\b', r'\bhow (do|can) i improve\b', r'\bimprove (my )?(profit|sales|margin|business)\b',
        r'\bsuggest', r'\brecommend', r'\bany (advice|tips|ideas)\b', r'\bhow to (grow|increase|boost)\b',
        r'\bwhat can i do\b',
    ],
    'explanation': [
        r'\bwhat is (the|a|my)? ?(health score|margin|profit|aov|forecast)\b',
        r'\bhow (do|is) .* (calculat|comput|work)', r'\bexplain (the|how)\b',
        r'\bwhat does .* mean\b', r'\bdefine\b', r'\bhow does .* work\b',
    ],
    'metric_lookup': [
        r'\bhow much\b', r'\bhow many\b', r'\btotal (revenue|sales|profit|orders)\b',
        r'\bwhat(?:\'s| is| was| were)? (my|the|our)? ?(revenue|sales|profit|margin|orders|aov|average)\b',
        r'\brevenue\b', r'\bsales\b', r'\bprofit\b', r'\borders?\b', r'\baverage (order|sale|ticket)\b',
        r'\bhow (did|are) (we|i|sales)\b', r'\b(selling|sold|performing)\b',
        r'\bhow (is|are|was|were)\b.*\bdoing\b',
    ],
    'greeting': [
        r'^\s*(hi|hey|hello|yo|howdy)\b', r'\bgood (morning|afternoon|evening)\b',
        r'^\s*thanks?\b', r'\bthank you\b', r'\bwhat can you (do|help)\b', r'\bhelp\b',
    ],
}

# Signals that a question is NOT about the business's data at all.
_OUT_OF_SCOPE = [
    r'\brecipe\b', r'\bhow (do i|to) (cook|make|prepare|bake)\b', r'\bingredients for\b',
    r'\bweather\b', r'\btell me a joke\b', r'\bcapital of\b', r'\btranslate\b',
    r'\bwho (won|is the president)\b', r'\bmeaning of life\b', r'\bwrite (me )?(a|an) (poem|essay|code)\b',
    r'\blegal\b', r'\btax law\b', r'\bmedical\b',
]

_COMPILED = {intent: [re.compile(p, re.IGNORECASE) for p in pats] for intent, pats in _PATTERNS.items()}
_OOS_RE = [re.compile(p, re.IGNORECASE) for p in _OUT_OF_SCOPE]

# Priority when scores tie — more specific / higher-value intents win.
_PRIORITY = [
    'diagnostic', 'forecast', 'comparison', 'recommendation', 'explanation',
    'trend', 'ranking', 'profitability', 'waste', 'inventory', 'staffing',
    'customer', 'metric_lookup', 'greeting',
]


def classify(text: str) -> dict:
    """
    Return { 'primary': intent, 'all': [intents by score], 'scores': {...} }.
    Combined questions surface multiple intents; `primary` is the best single
    label. Falls back to 'out_of_scope' or 'unclear' when nothing business-y
    matches.
    """
    t = text or ''
    scores: dict[str, int] = {}
    for intent, rxs in _COMPILED.items():
        s = sum(1 for rx in rxs if rx.search(t))
        if s:
            scores[intent] = s

    # A bare metric word (revenue/sales/profit/orders) implies metric_lookup.
    if 'metric_lookup' not in scores and re.search(r'\b(revenue|sales|profit|orders?|margin)\b', t, re.IGNORECASE):
        scores['metric_lookup'] = 1

    if not scores:
        if any(rx.search(t) for rx in _OOS_RE):
            return {'primary': 'out_of_scope', 'all': ['out_of_scope'], 'scores': {}}
        return {'primary': 'unclear', 'all': ['unclear'], 'scores': {}}

    # Out-of-scope wins only if it matches AND there's no real business signal.
    business_signal = any(i for i in scores if i not in ('greeting',))
    if any(rx.search(t) for rx in _OOS_RE) and not business_signal:
        return {'primary': 'out_of_scope', 'all': ['out_of_scope'], 'scores': {}}

    # metric_lookup and greeting are the "default" bucket: a specialized intent
    # (forecast, diagnostic, comparison, ...) should win even if a generic metric
    # word matched more times. Rank by tier first, then score, then priority.
    weak = {'metric_lookup', 'greeting'}

    def sort_key(intent: str):
        tier = 1 if intent in weak else 0
        pr = _PRIORITY.index(intent) if intent in _PRIORITY else len(_PRIORITY)
        return (tier, -scores[intent], pr)

    ordered = sorted(scores, key=sort_key)
    return {'primary': ordered[0], 'all': ordered, 'scores': scores}
