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

    # Persist a prediction record so the dashboard knows analysis has run
    col.predictions().insert_one({
        'business_id': bid,
        'type': 'full_analysis',
        'summary': {k: v for k, v in results.items() if not isinstance(v, dict) or 'error' not in v},
        'created_at': datetime.now(timezone.utc),
    })

    return results
