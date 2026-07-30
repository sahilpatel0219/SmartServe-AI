from datetime import datetime as _dt, time as _time

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from mongo import collections as col
from mongo.client import ping as mongo_ping
from .tenancy import require_business


class DashboardView(APIView):
    """Same KPI/readiness computation as the old core.views.dashboard_view, as JSON."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business, membership = require_business(request)
        bid = business.mongo_id

        kpis = {
            'today_revenue': None, 'today_orders': None, 'today_profit': None,
            'inventory_alerts': None, 'food_waste': None, 'forecasted_sales': None,
            'health_score': None, 'active_customers': None,
        }

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

        kpi_date = None
        if has_sales:
            latest = list(col.sales_records().find({'business_id': bid}, {'date': 1}).sort('date', -1).limit(1))
            if latest:
                kpi_date = latest[0].get('date')
                pipeline = [
                    {'$match': {'business_id': bid, 'date': kpi_date}},
                    {'$group': {'_id': None, 'revenue': {'$sum': '$revenue'}, 'cost': {'$sum': '$cost'}}},
                ]
                result = list(col.sales_records().aggregate(pipeline))
                if result:
                    rev = result[0].get('revenue', 0) or 0
                    cost = result[0].get('cost', 0) or 0
                    kpis['today_revenue'] = rev
                    kpis['today_profit'] = rev - cost

        if has_orders:
            latest_o = list(col.orders().find({'business_id': bid}, {'created_at': 1}).sort('created_at', -1).limit(1))
            if latest_o:
                last_dt = latest_o[0].get('created_at')
                if isinstance(last_dt, _dt):
                    day_start = _dt.combine(last_dt.date(), _time.min, tzinfo=last_dt.tzinfo)
                    day_end = _dt.combine(last_dt.date(), _time.max, tzinfo=last_dt.tzinfo)
                    kpis['today_orders'] = col.orders().count_documents({
                        'business_id': bid,
                        'created_at': {'$gte': day_start, '$lte': day_end},
                    })

        if has_inventory:
            kpis['inventory_alerts'] = col.inventory().count_documents({
                'business_id': bid,
                '$expr': {'$lte': ['$quantity', '$reorder_level']},
            })

        if has_customers:
            kpis['active_customers'] = col.customers().count_documents({'business_id': bid})

        pred = col.predictions().find_one({'business_id': bid, 'type': 'full_analysis'}, sort=[('created_at', -1)])
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

        latest_insights = list(col.insights().find(
            {'business_id': bid}, {'text': 1}, sort=[('created_at', -1)], limit=4
        ))
        for i in latest_insights:
            i['_id'] = str(i['_id'])

        return Response({
            'business': {'id': business.id, 'name': business.name},
            'mongo_ok': mongo_ping(),
            'kpis': kpis,
            'kpi_date': kpi_date,
            'data_readiness': {'score': readiness_score, 'items': readiness_items},
            'latest_insights': latest_insights,
        })
