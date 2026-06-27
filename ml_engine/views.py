"""
ML Engine views: trigger analysis, show results, display insights.
All data comes from the business's own uploaded records — never mocked.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Membership
from mongo import collections as col


def _get_business(request):
    m = Membership.objects.filter(user=request.user, is_active=True).select_related('business').first()
    return (m.business, m) if m else (None, None)


@login_required
def index_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id

    sales_count = col.sales_records().count_documents({'business_id': bid})
    predictions = list(col.predictions().find({'business_id': bid}, sort=[('created_at', -1)], limit=1))
    latest = predictions[0] if predictions else None
    insights = list(col.insights().find({'business_id': bid}, sort=[('created_at', -1)], limit=5))

    return render(request, 'ml_engine/index.html', {
        'business': business,
        'sales_count': sales_count,
        'has_enough': sales_count >= 30,
        'latest': latest,
        'insights': insights,
    })


@login_required
def analyze_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id

    sales_count = col.sales_records().count_documents({'business_id': bid})
    if sales_count < 30:
        messages.warning(request, f'AI analysis requires at least 30 sales records. You have {sales_count}. Upload more data first.')
        return redirect('onboarding:upload_center')

    return render(request, 'ml_engine/analyze.html', {
        'business': business,
        'sales_count': sales_count,
    })


@login_required
def run_analysis_view(request):
    if request.method != 'POST':
        return redirect('ml_engine:analyze')

    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')

    try:
        from ml_engine.services.pipeline import run_full_analysis
        run_full_analysis(business.mongo_id)
        messages.success(request, 'Analysis complete! Your AI insights and forecasts are ready below.')
    except ValueError as e:
        messages.warning(request, str(e))
    except Exception as e:
        messages.error(request, f'Analysis failed: {e}')

    return redirect('ml_engine:results')


@login_required
def results_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id

    predictions = list(col.predictions().find({'business_id': bid}, sort=[('created_at', -1)], limit=1))
    if not predictions:
        messages.info(request, 'No analysis results yet. Run the analysis first.')
        return redirect('ml_engine:analyze')

    latest = predictions[0]
    insights = list(col.insights().find({'business_id': bid}, sort=[('created_at', -1)]))

    # Unpack forecast data for Chart.js (canonical doc stores daily_forecast list)
    forecast = latest.get('forecast', {})
    daily = forecast.get('daily_forecast', []) if isinstance(forecast, dict) else []
    forecast_dates = [d['date'] for d in daily]
    forecast_values = [round(float(d['predicted_revenue']), 2) for d in daily]

    # Profitability / menu engineering
    profitability = latest.get('profitability', {})
    menu_matrix = profitability.get('menu_matrix', {})
    stars = menu_matrix.get('Stars', [])
    plowhorses = menu_matrix.get('Plowhorses', [])
    puzzles = menu_matrix.get('Puzzles', [])
    dogs = menu_matrix.get('Dogs', [])

    # Health score components
    health = latest.get('health_score', {})

    # Waste
    waste = latest.get('waste', {})
    waste_items = waste.get('high_waste_items', [])[:5]

    return render(request, 'ml_engine/results.html', {
        'business': business,
        'latest': latest,
        'insights': insights,
        'forecast_dates': forecast_dates,
        'forecast_values': forecast_values,
        'profitability': profitability,
        'stars': stars,
        'plowhorses': plowhorses,
        'puzzles': puzzles,
        'dogs': dogs,
        'health': health,
        'waste_items': waste_items,
    })


@login_required
def insights_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    insights = list(col.insights().find({'business_id': bid}, sort=[('created_at', -1)]))

    if not insights:
        return render(request, 'ml_engine/insights.html', {
            'business': business,
            'insights': [],
            'has_insights': False,
        })

    # Group by category
    by_cat = {}
    for ins in insights:
        cat = ins.get('category', 'General')
        by_cat.setdefault(cat, []).append(ins)

    return render(request, 'ml_engine/insights.html', {
        'business': business,
        'insights': insights,
        'by_cat': by_cat,
        'has_insights': True,
    })
