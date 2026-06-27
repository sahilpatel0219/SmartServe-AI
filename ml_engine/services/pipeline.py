"""
Full ML analysis pipeline for a single business.
Called synchronously for the MVP; designed to be moved to Celery later.
Each step checks for sufficient data before running.
"""
from datetime import datetime, timezone

from mongo import collections as col
from .forecasting import run_sales_forecast
from .profitability import run_profitability_analysis
from .waste import run_waste_prediction
from .health_score import compute_health_score
from .insights import generate_insights


MIN_SALES_ROWS = 30  # minimum to run any forecasting


def run_full_analysis(business_id: str) -> dict:
    """
    Entry point: orchestrates all ML sub-tasks.
    Returns a summary dict; also persists results to MongoDB.
    Raises ValueError if insufficient data.
    """
    bid = str(business_id)
    sales_count = col.sales_records().count_documents({'business_id': bid})

    if sales_count < MIN_SALES_ROWS:
        raise ValueError(
            f'Need at least {MIN_SALES_ROWS} days of sales data to run analysis. '
            f'You have {sales_count} records — please upload more sales history.'
        )

    results = {}

    # 1. Sales forecast
    try:
        results['forecast'] = run_sales_forecast(bid)
    except Exception as e:
        results['forecast'] = {'error': str(e)}

    # 2. Profitability
    try:
        results['profitability'] = run_profitability_analysis(bid)
    except Exception as e:
        results['profitability'] = {'error': str(e)}

    # 3. Waste prediction
    try:
        results['waste'] = run_waste_prediction(bid)
    except Exception as e:
        results['waste'] = {'error': str(e)}

    # 4. Health score
    try:
        results['health_score'] = compute_health_score(bid)
    except Exception as e:
        results['health_score'] = {'error': str(e)}

    # 5. Natural-language insights
    try:
        results['insights'] = generate_insights(bid, results)
    except Exception as e:
        results['insights'] = {'error': str(e)}

    # ── Assemble a canonical prediction document ──────────────────────────────
    # The dashboard, results page and templates all read fixed top-level keys, so
    # we transform each sub-result into the exact shape they expect.
    doc = _build_prediction_doc(bid, results)
    col.predictions().insert_one(doc)

    return results


def _build_prediction_doc(bid: str, results: dict) -> dict:
    """Transform raw sub-service outputs into the document shape the UI reads."""
    now = datetime.now(timezone.utc)

    # ── Forecast: flatten daily_forecast → {date: value} map + total ──────────
    forecast_raw = results.get('forecast', {})
    daily = forecast_raw.get('daily_forecast', []) if isinstance(forecast_raw, dict) else []
    forecast_map = {d['date']: d['predicted_revenue'] for d in daily}
    total_forecast = round(sum(d['predicted_revenue'] for d in daily), 2)

    # ── Profitability: bucket items into the menu-engineering matrix ──────────
    prof_raw = results.get('profitability', {})
    prof_items = prof_raw.get('items', []) if isinstance(prof_raw, dict) else []
    plural = {'Star': 'Stars', 'Plowhorse': 'Plowhorses', 'Puzzle': 'Puzzles', 'Dog': 'Dogs'}
    menu_matrix = {'Stars': [], 'Plowhorses': [], 'Puzzles': [], 'Dogs': []}
    for it in prof_items:
        bucket = plural.get(it.get('classification'))
        if bucket:
            menu_matrix[bucket].append(it)

    # ── Waste: rename fields to what the results template renders ─────────────
    waste_raw = results.get('waste', {})
    at_risk = waste_raw.get('at_risk_items', []) if isinstance(waste_raw, dict) else []
    high_waste_items = [{
        'item':            w.get('item', ''),
        'current_stock':   w.get('quantity', 0),
        'daily_use':       w.get('daily_use', 0),
        'days_to_expiry':  w.get('days_until_expiry'),
        'estimated_loss':  w.get('estimated_loss_inr', 0),
    } for w in at_risk]
    waste_loss = waste_raw.get('total_estimated_loss_inr', 0) if isinstance(waste_raw, dict) else 0

    health_raw = results.get('health_score', {})
    if not isinstance(health_raw, dict) or 'error' in health_raw:
        health_raw = {}

    return {
        'business_id': bid,
        'type': 'full_analysis',
        'forecast': {
            'daily_forecast': daily,
            'map': forecast_map,
            'total_forecast': total_forecast,
            'item_demand': forecast_raw.get('item_demand', []) if isinstance(forecast_raw, dict) else [],
        },
        'profitability': {
            'menu_matrix': menu_matrix,
            'total_profit': prof_raw.get('total_profit') if isinstance(prof_raw, dict) else None,
            'overall_margin': prof_raw.get('overall_margin') if isinstance(prof_raw, dict) else None,
        },
        'waste': {
            'high_waste_items': high_waste_items,
            'estimated_loss_inr': waste_loss,
        },
        'health_score': health_raw,
        'created_at': now,
    }
