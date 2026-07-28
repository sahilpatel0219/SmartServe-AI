"""
Orchestrator — the fallback-mode brain that replaces the keyword matcher.

Pipeline: question → injection check → intent → entities → tool selection →
deterministic computation → templated answer. Identical tool layer to LLM mode
(step 4); only understanding + phrasing differ. Fully testable with no API key.

`answer()` returns {'reply', 'chips', 'intent', 'ok', 'needs_clarification'}.
"""
from __future__ import annotations

from datetime import date, timedelta

from assistant import intents, entities, guards, composer, context as ctx
from assistant.tools import datasource, functions as fn


def _prev_period(start: date, end: date) -> tuple[date, date]:
    span = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    return prev_end - timedelta(days=span - 1), prev_end


def _default_window(today: date, days: int) -> tuple[date, date]:
    return today - timedelta(days=days - 1), today


def _greeting_reply(biz_name: str) -> str:
    return (f"Hi! I'm the SmartServe assistant for {biz_name}. I answer from your own uploaded "
            "data — ask me about revenue, profit, orders, top items, trends, forecasts, stock, "
            "waste, customers, busiest times, or your health score.")


def _explanation_reply(text: str) -> str:
    t = text.lower()
    if 'health score' in t:
        return ("The health score (0–100) blends several signals from your data — sales level, "
                "profitability, inventory health, and growth — into one number. Higher is better; "
                "the AI Results page shows each component.")
    if 'margin' in t:
        return ("Margin = (revenue − cost) ÷ revenue, shown as a percentage. It needs a cost column "
                "in your sales upload. Profit is revenue − cost in rupees.")
    if 'forecast' in t:
        return ("The forecast is trained on your own sales history (a model over daily totals with "
                "day-of-week and recent-sales features) to estimate the next few days. It's an "
                "estimate, never a guarantee.")
    if 'aov' in t or 'average order' in t:
        return "Average order value = total revenue ÷ number of orders over the period."
    return ("I explain figures from your own data — try 'what is the health score', "
            "'how is margin calculated', or 'how does the forecast work'.")


def _recommendation(business_id, role) -> str:
    tips = []
    hs = fn.get_health_score(business_id)
    if hs.get('data_sufficient') and hs.get('weakest'):
        tips.append(f"your weakest health area is {hs['weakest'].replace('_', ' ')} — focus there")
    low = fn.get_low_stock(business_id)
    if low.get('ok') and low.get('count'):
        tips.append(f"reorder {low['count']} low-stock item(s) before you run out")
    waste = fn.get_waste_risk(business_id)
    if waste.get('data_sufficient') and waste.get('estimated_loss'):
        tips.append(f"cut waste — about {composer.money(waste['estimated_loss'])} is at risk")
    if not tips:
        return ("Upload your sales, inventory and run the AI analysis, and I'll give targeted "
                "suggestions from your own numbers.")
    return "A few data-backed moves: " + "; ".join(tips) + "."


def answer(question: str, business_id, role: str, biz_name: str,
           user_id=None, today: date | None = None, context: list | None = None) -> dict:
    text = (question or '').strip()
    today = today or date.today()

    def out(reply, intent, ok=True, chips=None, needs_clarification=False, ent_snap=None):
        return {'reply': reply, 'intent': intent, 'ok': ok,
                'chips': chips if chips is not None else composer.chips_for(intent),
                'needs_clarification': needs_clarification, '_ent': ent_snap}

    def gap_if_needed(result, reply, intent):
        if result.get('data_sufficient') is False and not result.get('denied'):
            guards.log_gap(business_id, user_id, text, intent, result.get('need') or 'insufficient_data')
        return reply

    # Dispatch a resolved (intent, entities) pair to the right tool + renderer.
    def dispatch(intent, ent):
        item = (ent.get('item') or {}).get('match')
        metric = ent.get('metric')
        tr = ent.get('time_range')
        snap = ctx.snapshot(ent)

        if intent == 'metric_lookup':
            tl2 = text.lower()
            if ('average' in tl2 and ('order' in tl2 or 'sale' in tl2 or 'transaction' in tl2)) or 'aov' in tl2:
                s, e = (tr['start'], tr['end']) if tr else _default_window(today, 30)
                rev = fn.get_metric(business_id, role, 'revenue', s, e)
                orders = fn.get_metric(business_id, role, 'orders', s, e)
                if rev.get('data_sufficient') and orders.get('value'):
                    aov = rev['value'] / orders['value']
                    return out(f"Your average order value{composer._win(rev)} is {composer.money(aov)} "
                               f"({composer.money(rev['value'])} over {int(orders['value'])} orders).",
                               'metric_lookup', ent_snap=snap)
                return out(gap_if_needed(rev, f"{composer._NEED_MESSAGES['sales']} {composer.UPLOAD_HINT}", intent),
                           'metric_lookup', ok=False, ent_snap=snap)
            m = metric or 'revenue'
            s, e = (tr['start'], tr['end']) if tr else _default_window(today, 7)
            res = fn.get_metric(business_id, role, m, s, e, item=item, category=ent.get('category'))
            return out(gap_if_needed(res, composer.render_metric(res, ent), intent), 'metric_lookup',
                       ok=res.get('ok', True) and res.get('data_sufficient', True), ent_snap=snap)

        if intent == 'comparison':
            m = metric or 'revenue'
            a = (tr['start'], tr['end']) if tr else (today.replace(day=1), today)
            b = _prev_period(*a)
            res = fn.compare_periods(business_id, role, m, a, b, item=item)
            return out(gap_if_needed(res, composer.render_comparison(res, ent), intent), 'comparison', ent_snap=snap)

        if intent == 'ranking':
            m = metric if metric in ('revenue', 'quantity', 'profit', 'margin') else 'revenue'
            asc = any(w in text.lower() for w in ('worst', 'least', 'bottom', 'lowest', 'poorly'))
            s, e = (tr['start'], tr['end']) if tr else _default_window(today, 30)
            res = fn.rank_items(business_id, role, m, s, e, limit=5, ascending=asc)
            return out(gap_if_needed(res, composer.render_ranking(res, ent), intent), 'ranking', ent_snap=snap)

        if intent == 'trend':
            m = metric or 'revenue'
            s, e = (tr['start'], tr['end']) if tr else _default_window(today, 30)
            span = (e - s).days
            gran = 'month' if span > 90 else 'week' if span > 21 else 'day'
            res = fn.get_trend(business_id, role, m, s, e, gran)
            return out(gap_if_needed(res, composer.render_trend(res, ent), intent), 'trend', ent_snap=snap)

        if intent == 'forecast':
            res = fn.get_forecast(business_id, item=item)
            return out(gap_if_needed(res, composer.render_forecast(res, ent), intent), 'forecast', ent_snap=snap)

        if intent == 'inventory':
            tl2 = text.lower()
            if 'reorder' in tl2 or 'restock' in tl2 or 'what should i buy' in tl2 or 'what should i order' in tl2:
                res = fn.get_reorder_suggestions(business_id)
                return out(gap_if_needed(res, composer.render_reorder(res, ent), intent), 'inventory', ent_snap=snap)
            if 'expir' in tl2 or 'expire' in tl2:
                res = fn.get_expiring_soon(business_id)
                return out(gap_if_needed(res, composer.render_expiring(res, ent), intent), 'inventory', ent_snap=snap)
            res = fn.get_low_stock(business_id)
            return out(gap_if_needed(res, composer.render_inventory_low(res, ent), intent), 'inventory', ent_snap=snap)

        if intent == 'profitability':
            res = fn.get_item_profitability(business_id, role, item=item)
            return out(gap_if_needed(res, composer.render_profitability(res, ent), intent), 'profitability', ent_snap=snap)

        if intent == 'waste':
            res = fn.get_waste_risk(business_id)
            return out(gap_if_needed(res, composer.render_waste(res, ent), intent), 'waste', ent_snap=snap)

        if intent == 'customer':
            res = fn.get_customer_stats(business_id, segment=ent.get('segment'))
            return out(gap_if_needed(res, composer.render_customer(res, ent), intent), 'customer', ent_snap=snap)

        if intent == 'staffing':
            res = fn.get_peak_times(business_id)
            return out(gap_if_needed(res, composer.render_staffing(res, ent), intent), 'staffing', ent_snap=snap)

        if intent == 'diagnostic':
            a = (tr['start'], tr['end']) if tr else ((today - timedelta(days=1),) * 2)
            res = fn.explain_sales_change(business_id, role, a)
            return out(gap_if_needed(res, composer.render_diagnostic(res, ent), intent), 'diagnostic', ent_snap=snap)

        guards.log_gap(business_id, user_id, text, intent, 'no_route')
        return out("I couldn't map that to your data. Try asking about sales, stock, or forecasts.",
                   'unclear', ok=False)

    if not text:
        return out("Ask me anything about your business data.", 'greeting')

    # 1) Prompt-injection: treat as untrusted; refuse instruction-like requests.
    suspicious, matched = guards.detect_injection(text)
    if suspicious:
        guards.log_security_event(business_id, user_id, text, 'injection', matched)
        return out("I can only answer questions about your own business data — I can't change my "
                   "rules or access anything outside your account. Try asking about sales, stock, "
                   "or forecasts.", 'out_of_scope', ok=False)

    # 2) Follow-up ("what about last month?", "and pizza?", "why?") → inherit the
    #    previous turn's intent + entities, overlay anything new, and dispatch.
    if context and ctx.is_followup(text):
        prev = context[-1]
        catalog = datasource.catalog_names(business_id)
        categories = datasource.category_names(business_id)
        new_ent = entities.extract_entities(text, catalog, categories, today=today)
        fu_intent, fu_ent = ctx.merge(prev, new_ent, text)
        return dispatch(fu_intent, fu_ent)

    # Health score is a well-known named metric — route it directly.
    tl = text.lower()
    if 'health score' in tl or ('health' in tl and 'score' in tl) or 'how am i doing' in tl \
            or ('how is' in tl and 'business' in tl):
        res = fn.get_health_score(business_id)
        if res.get('data_sufficient') is False:
            guards.log_gap(business_id, user_id, text, 'health', res.get('need') or 'insufficient')
        return out(composer.render_health(res, {}), 'health')

    cls = intents.classify(text)
    intent = cls['primary']

    if intent == 'greeting':
        return out(_greeting_reply(biz_name), 'greeting')
    if intent == 'out_of_scope':
        guards.log_gap(business_id, user_id, text, intent, 'out_of_scope')
        return out("That's outside what I can answer from your business data. I can help with sales, "
                   "profit, orders, stock, forecasts, customers and more.", 'out_of_scope', ok=False)
    if intent == 'unclear':
        guards.log_gap(business_id, user_id, text, intent, 'unclear')
        return out("I couldn't quite understand that. Try asking about sales, profit, top items, "
                   "stock, forecasts, or your busiest day.", 'unclear', ok=False)
    if intent == 'explanation':
        return out(_explanation_reply(text), 'explanation')
    if intent == 'recommendation':
        return out(_recommendation(business_id, role), 'health')

    # Entities (needs the business's real catalog / categories)
    catalog = datasource.catalog_names(business_id)
    categories = datasource.category_names(business_id)
    ent = entities.extract_entities(text, catalog, categories, today=today)

    # Item ambiguity → ask which one (one short clarifying question).
    if ent['item']['ambiguous'] and intent in ('metric_lookup', 'ranking', 'trend', 'profitability', 'diagnostic'):
        cands = ent['item']['candidates']
        return out(f"Which one did you mean — {', or '.join(cands)}?", intent,
                   chips=cands, needs_clarification=True)

    return dispatch(intent, ent)
