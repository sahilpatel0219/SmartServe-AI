from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from mongo.client import ping as mongo_ping


@login_required
def dashboard_view(request):
    from core.utils import get_active_membership
    membership = get_active_membership(request)

    if not membership:
        return redirect('onboarding:create_business')

    business = membership.business

    # KPIs are None until real data is uploaded — no fake numbers
    kpis = {
        'today_revenue': None,
        'today_orders': None,
        'today_profit': None,
        'inventory_alerts': None,
        'food_waste': None,
        'forecasted_sales': None,
        'health_score': None,
        'active_customers': None,
    }

    # Data readiness check
    from mongo import collections as col
    bid = business.mongo_id
    has_sales = col.sales_records().count_documents({'business_id': bid}) > 0
    has_inventory = col.inventory().count_documents({'business_id': bid}) > 0
    has_menu = col.menu_items().count_documents({'business_id': bid}) > 0
    has_orders = col.orders().count_documents({'business_id': bid}) > 0
    has_customers = col.customers().count_documents({'business_id': bid}) > 0

    readiness_items = [
        {'label': 'Sales Data', 'done': has_sales},
        {'label': 'Inventory', 'done': has_inventory},
        {'label': 'Menu', 'done': has_menu},
        {'label': 'Orders', 'done': has_orders},
        {'label': 'Customers', 'done': has_customers},
    ]
    done_count = sum(1 for i in readiness_items if i['done'])
    readiness_score = int((done_count / len(readiness_items)) * 100)

    data_readiness = {
        'score': readiness_score,
        'items': readiness_items,
    }

    # Load real KPIs if data exists.
    # Data is typically historical, so KPIs reflect the most recent day that has data
    # rather than the literal calendar date (which usually has no sales yet).
    kpi_date = None
    if has_sales:
        # Find the most recent date present in the sales data
        latest = list(col.sales_records().find(
            {'business_id': bid}, {'date': 1}
        ).sort('date', -1).limit(1))
        if latest:
            kpi_date = latest[0].get('date')
            pipeline = [
                {'$match': {'business_id': bid, 'date': kpi_date}},
                {'$group': {
                    '_id': None,
                    'revenue': {'$sum': '$revenue'},
                    'cost':    {'$sum': '$cost'},
                }},
            ]
            result = list(col.sales_records().aggregate(pipeline))
            if result:
                rev = result[0].get('revenue', 0) or 0
                cost = result[0].get('cost', 0) or 0
                kpis['today_revenue'] = rev
                kpis['today_profit'] = rev - cost

    # Orders on the most recent order date
    if has_orders:
        latest_o = list(col.orders().find(
            {'business_id': bid}, {'created_at': 1}
        ).sort('created_at', -1).limit(1))
        if latest_o:
            from datetime import datetime as _dt, time as _time
            last_dt = latest_o[0].get('created_at')
            if isinstance(last_dt, _dt):
                day_start = _dt.combine(last_dt.date(), _time.min, tzinfo=last_dt.tzinfo)
                day_end = _dt.combine(last_dt.date(), _time.max, tzinfo=last_dt.tzinfo)
                kpis['today_orders'] = col.orders().count_documents({
                    'business_id': bid,
                    'created_at': {'$gte': day_start, '$lte': day_end},
                })

    if has_inventory:
        # quantity / reorder_level are numeric after normalisation
        low_stock = col.inventory().count_documents({
            'business_id': bid,
            '$expr': {'$lte': ['$quantity', '$reorder_level']}
        })
        kpis['inventory_alerts'] = low_stock

    if has_customers:
        kpis['active_customers'] = col.customers().count_documents({'business_id': bid})

    # AI-derived KPIs from the latest full-analysis run (if any)
    pred = col.predictions().find_one(
        {'business_id': bid, 'type': 'full_analysis'}, sort=[('created_at', -1)]
    )
    if pred:
        waste = pred.get('waste', {}).get('estimated_loss_inr')
        if waste is not None:
            kpis['food_waste'] = waste
        total_fc = pred.get('forecast', {}).get('total_forecast')
        if total_fc is not None:
            kpis['forecasted_sales'] = total_fc
        hs = pred.get('health_score', {}).get('total_score')
        if hs is not None:
            kpis['health_score'] = round(hs)

    # Latest AI insights (if any exist from a prior analysis run)
    latest_insights = list(col.insights().find(
        {'business_id': bid}, {'text': 1}, sort=[('created_at', -1)], limit=4
    ))

    return render(request, 'core/dashboard.html', {
        'business': business,
        'membership': membership,
        'mongo_ok': mongo_ping(),
        'kpis': kpis,
        'kpi_date': kpi_date,
        'data_readiness': data_readiness,
        'latest_insights': latest_insights,
    })


def landing_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    # Icon colors are handled by the .feature-card__icon class (theme token),
    # so feature dicts carry only content — no presentation/hex here.
    features = [
        {'icon': 'receipt', 'title': 'Order Management', 'desc': 'Counter, QR, delivery, phone — manage all orders in one live board.'},
        {'icon': 'box-seam', 'title': 'Smart Inventory', 'desc': 'Auto-deduct stock when orders are placed. Get alerted before you run out.'},
        {'icon': 'bar-chart-line', 'title': 'Real-Time Analytics', 'desc': 'Daily revenue, profit, top items, and busiest hours — from your own data.'},
        {'icon': 'cpu', 'title': 'AI Forecasting', 'desc': 'Demand forecasts, waste prediction, and a health score — trained on your data.'},
        {'icon': 'chat-dots', 'title': 'AI Assistant', 'desc': 'Ask questions in plain language. Get answers from your own business metrics.'},
        {'icon': 'people', 'title': 'Team & Suppliers', 'desc': 'Manage staff shifts, attendance, suppliers, and purchase orders in one place.'},
    ]

    return render(request, 'core/landing.html', {'features': features})


def styleguide_view(request):
    """
    Living style guide — renders every component and state in the Noir Crimson
    theme on a single page for review. Standalone (no auth/chrome) so the design
    system can be inspected in isolation. Presentation only; no business data.
    """
    return render(request, 'core/styleguide.html')


def handler404(request, exception):
    return render(request, 'core/404.html', status=404)


def handler500(request):
    return render(request, 'core/500.html', status=500)
