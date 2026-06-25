"""
Auto-generates natural-language insights from computed analytics results.
All numbers come from real data — no templates with fake figures.
"""
from datetime import datetime, timezone
from mongo import collections as col


def generate_insights(business_id: str, analysis_results: dict) -> list:
    """Build insight strings from the analysis_results dict and persist them."""
    texts = []

    # Forecast insights
    forecast = analysis_results.get('forecast', {})
    if 'daily_forecast' in forecast:
        next_7 = forecast['daily_forecast']
        if next_7:
            total_7d = sum(d['predicted_revenue'] for d in next_7)
            peak = max(next_7, key=lambda d: d['predicted_revenue'])
            texts.append(
                f"Forecasted revenue for the next 7 days is ₹{total_7d:,.0f}. "
                f"Highest expected on {peak['date']} (₹{peak['predicted_revenue']:,.0f})."
            )

    if 'item_demand' in forecast and forecast['item_demand']:
        top = forecast['item_demand'][0]
        texts.append(
            f"'{top['item']}' is your highest-demand item — avg {top['avg_daily_qty']} units/day over the last 30 days."
        )

    # Profitability insights
    profit = analysis_results.get('profitability', {})
    if 'items' in profit and profit['items']:
        stars = [i for i in profit['items'] if i.get('classification') == 'Star']
        dogs = [i for i in profit['items'] if i.get('classification') == 'Dog']
        if stars:
            texts.append(
                f"Star items (high sales + high margin): {', '.join(i['item'] for i in stars[:3])}. "
                f"Keep them prominently featured on your menu."
            )
        if dogs:
            texts.append(
                f"Underperforming items (low sales + low margin): {', '.join(i['item'] for i in dogs[:3])}. "
                f"Consider removing or repricing these."
            )
        if profit.get('overall_margin'):
            texts.append(f"Overall profit margin is {profit['overall_margin']:.1f}%.")

    # Waste insights
    waste = analysis_results.get('waste', {})
    if waste.get('at_risk_items'):
        n = len(waste['at_risk_items'])
        loss = waste.get('total_estimated_loss_inr', 0)
        texts.append(
            f"{n} inventory item(s) are at risk of expiry — estimated loss of ₹{loss:,.0f} "
            f"if not used in time."
        )
        soonest = waste['at_risk_items'][0]
        texts.append(
            f"Most urgent: '{soonest['item']}' — {soonest.get('risk_reason', '')}."
        )

    # Health score insights
    health = analysis_results.get('health_score', {})
    if health.get('total_score') is not None:
        score = health['total_score']
        grade = health.get('grade', '')
        texts.append(
            f"Business Health Score: {score}/100 (Grade {grade}). "
            + ("Strong performance across the board." if score >= 75
               else "Several areas need attention — see the breakdown." if score >= 50
               else "Significant improvements needed in core metrics.")
        )
        # Weakest component
        components = health.get('components', {})
        if components:
            weakest = min(components, key=components.get)
            texts.append(
                f"Weakest area: {weakest.replace('_', ' ').title()} "
                f"({components[weakest]}/20 pts). "
                f"{health.get('reasons', {}).get(weakest, '')}"
            )

    # Persist each insight
    now = datetime.now(timezone.utc)
    if texts:
        col.insights().delete_many({'business_id': business_id})  # replace old ones
        col.insights().insert_many([{
            'business_id': business_id,
            'text': t,
            'category': _categorise(t),
            'created_at': now,
        } for t in texts])

    return texts


def _categorise(text: str) -> str:
    t = text.lower()
    if 'forecast' in t or 'predict' in t:
        return 'Forecast'
    if 'margin' in t or 'profit' in t or 'revenue' in t:
        return 'Profitability'
    if 'expir' in t or 'waste' in t or 'loss' in t:
        return 'Waste'
    if 'health' in t or 'score' in t:
        return 'Health'
    if 'demand' in t or 'item' in t:
        return 'Demand'
    return 'General'
