from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from mongo.client import ping as mongo_ping


@login_required
def dashboard_view(request):
    from accounts.models import Membership
    membership = Membership.objects.filter(
        user=request.user, is_active=True
    ).select_related('business').first()

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

    # Load real KPIs if data exists
    if has_sales:
        from datetime import date, timezone
        import datetime
        today_str = date.today().isoformat()
        pipeline = [
            {'$match': {'business_id': bid, 'date': today_str}},
            {'$group': {'_id': None, 'total': {'$sum': '$revenue'}, 'count': {'$sum': 1}}},
        ]
        result = list(col.sales_records().aggregate(pipeline))
        if result:
            kpis['today_revenue'] = result[0].get('total', 0)
            kpis['today_orders'] = result[0].get('count', 0)

    if has_inventory:
        low_stock = col.inventory().count_documents({
            'business_id': bid,
            '$expr': {'$lte': ['$quantity', '$reorder_level']}
        })
        kpis['inventory_alerts'] = low_stock

    if has_customers:
        kpis['active_customers'] = col.customers().count_documents({'business_id': bid})

    # Latest AI insights (if any exist from a prior analysis run)
    latest_insights = list(col.insights().find(
        {'business_id': bid}, {'text': 1}, sort=[('created_at', -1)], limit=4
    ))

    return render(request, 'core/dashboard.html', {
        'business': business,
        'membership': membership,
        'mongo_ok': mongo_ping(),
        'kpis': kpis,
        'data_readiness': data_readiness,
        'latest_insights': latest_insights,
    })


def landing_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    features = [
        {'icon': 'receipt', 'title': 'Order Management', 'desc': 'Counter, QR, delivery, phone — manage all orders in one live board.', 'bg': '#E8F5EF', 'color': '#2D6A4F'},
        {'icon': 'box-seam', 'title': 'Smart Inventory', 'desc': 'Auto-deduct stock when orders are placed. Get alerted before you run out.', 'bg': '#FEF3DD', 'color': '#E8A33D'},
        {'icon': 'bar-chart-line', 'title': 'Real-Time Analytics', 'desc': 'Daily revenue, profit, top items, and busiest hours — from your own data.', 'bg': '#DBEAFE', 'color': '#2563EB'},
        {'icon': 'cpu', 'title': 'AI Forecasting', 'desc': 'Demand forecasts, waste prediction, and a health score — trained on your data.', 'bg': '#E8F5EF', 'color': '#2D6A4F'},
        {'icon': 'chat-dots', 'title': 'AI Assistant', 'desc': 'Ask questions in plain language. Get answers from your own business metrics.', 'bg': '#FEF3DD', 'color': '#E8A33D'},
        {'icon': 'people', 'title': 'Team & Suppliers', 'desc': 'Manage staff shifts, attendance, suppliers, and purchase orders in one place.', 'bg': '#DBEAFE', 'color': '#2563EB'},
    ]

    return render(request, 'core/landing.html', {'features': features})


def handler404(request, exception):
    return render(request, 'core/404.html', status=404)


def handler500(request):
    return render(request, 'core/500.html', status=500)
