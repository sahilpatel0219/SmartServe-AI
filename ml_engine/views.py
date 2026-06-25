from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.models import Membership

@login_required
def index_view(request):
    membership = Membership.objects.filter(user=request.user, is_active=True).select_related('business').first()
    if not membership:
        return redirect('onboarding:create_business')
    business = membership.business
    from mongo import collections as col
    bid = business.mongo_id
    has_sales = col.sales_records().count_documents({'business_id': bid}) > 0
    predictions = list(col.predictions().find({'business_id': bid}, sort=[('created_at', -1)], limit=1))
    latest_prediction = predictions[0] if predictions else None
    return render(request, 'ml_engine/index.html', {
        'business': business,
        'has_sales': has_sales,
        'latest_prediction': latest_prediction,
    })

@login_required
def analyze_view(request):
    from accounts.models import Membership
    membership = Membership.objects.filter(user=request.user, is_active=True).select_related('business').first()
    if not membership:
        return redirect('onboarding:create_business')
    business = membership.business
    from mongo import collections as col
    bid = business.mongo_id
    has_sales = col.sales_records().count_documents({'business_id': bid}) >= 30
    if not has_sales:
        from django.contrib import messages
        messages.warning(request, 'AI analysis requires at least 30 days of sales data. Please upload your sales history first.')
        return redirect('onboarding:upload_center')
    return render(request, 'ml_engine/analyze.html', {'business': business})

@login_required
def run_analysis_view(request):
    """POST endpoint: run the full ML pipeline on uploaded data."""
    if request.method != 'POST':
        return redirect('ml_engine:analyze')

    membership = Membership.objects.filter(user=request.user, is_active=True).select_related('business').first()
    if not membership:
        return redirect('onboarding:create_business')

    business = membership.business
    from django.contrib import messages

    try:
        from ml_engine.services.pipeline import run_full_analysis
        run_full_analysis(business.mongo_id)
        messages.success(request, 'Analysis complete! Your insights and forecasts are ready.')
    except ValueError as e:
        messages.warning(request, str(e))
    except Exception as e:
        messages.error(request, f'Analysis failed: {e}')

    return redirect('ml_engine:insights')


@login_required
def insights_view(request):
    membership = Membership.objects.filter(user=request.user, is_active=True).select_related('business').first()
    if not membership:
        return redirect('onboarding:create_business')
    business = membership.business
    from mongo import collections as col
    bid = business.mongo_id
    insights = list(col.insights().find({'business_id': bid}, sort=[('created_at', -1)]))
    return render(request, 'ml_engine/insights.html', {'business': business, 'insights': insights})
