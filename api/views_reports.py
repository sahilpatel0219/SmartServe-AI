"""
Report exports return binary files (xlsx/pdf), which don't fit DRF's Response/
content-negotiation model cleanly, so these are plain Django views with manual
JWT authentication (see api/jwt_auth.py) instead of DRF APIViews. All the
actual export logic is reused unchanged from reports/views.py.
"""
import json

from django.http import HttpResponse, JsonResponse

from reports.views import (
    _period_cutoff, _export_sales, _export_inventory,
    _export_customers, _export_staff, _export_orders,
)
from mongo import collections as col
from .jwt_auth import require_authenticated_business


@require_authenticated_business
def reports_status_view(request):
    bid = request.api_business.mongo_id
    return JsonResponse({
        'has_sales': col.sales_records().count_documents({'business_id': bid}) > 0,
        'has_inventory': col.inventory().count_documents({'business_id': bid}) > 0,
        'has_customers': col.customers().count_documents({'business_id': bid}) > 0,
        'has_staff': col.employees().count_documents({'business_id': bid}) > 0,
        'has_orders': col.orders().count_documents({'business_id': bid}) > 0,
    })


@require_authenticated_business
def export_view(request, report_type, fmt):
    business = request.api_business
    bid = business.mongo_id
    period = request.GET.get('period', '30')
    cutoff, days = _period_cutoff(period)

    if report_type == 'sales':
        return _export_sales(bid, fmt, cutoff, days, business.name)
    elif report_type == 'inventory':
        return _export_inventory(bid, fmt, business.name)
    elif report_type == 'customers':
        return _export_customers(bid, fmt, business.name)
    elif report_type == 'staff':
        return _export_staff(bid, fmt, business.name)
    elif report_type == 'orders':
        return _export_orders(bid, fmt, business.name)
    return HttpResponse('Invalid report type', status=400)
