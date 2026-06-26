from datetime import datetime, timezone
from bson import ObjectId
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Membership
from mongo import collections as col


def _get_business(request):
    m = Membership.objects.filter(user=request.user, is_active=True).select_related('business').first()
    return (m.business, m) if m else (None, None)


def _segment(visits, total_spend):
    if total_spend >= 5000 or visits >= 20:
        return 'VIP'
    elif visits >= 5:
        return 'Regular'
    else:
        return 'Inactive'


@login_required
def index_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    segment_filter = request.GET.get('segment', '')
    custs = list(col.customers().find({'business_id': bid}, sort=[('name', 1)]))
    for c in custs:
        c['str_id'] = str(c.get('_id', ''))
        c['segment'] = _segment(c.get('visit_count', 0), c.get('total_spend', 0))
    if segment_filter:
        custs = [c for c in custs if c['segment'] == segment_filter]
    return render(request, 'customers/index.html', {
        'business': business,
        'customers': custs,
        'segment_filter': segment_filter,
        'segments': ['VIP', 'Regular', 'Inactive'],
    })


@login_required
def add_customer_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Customer name is required.')
        else:
            col.customers().insert_one({
                'business_id': bid,
                'name': name,
                'phone': request.POST.get('phone', '').strip(),
                'email': request.POST.get('email', '').strip(),
                'visit_count': 0,
                'total_spend': 0.0,
                'notes': request.POST.get('notes', '').strip(),
                'created_at': datetime.now(timezone.utc),
            })
            messages.success(request, f'Customer "{name}" added.')
            return redirect('customers:index')
    return render(request, 'customers/add.html', {'business': business})


@login_required
def detail_view(request, customer_id):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    customer = col.customers().find_one({'_id': ObjectId(customer_id), 'business_id': bid})
    if not customer:
        messages.error(request, 'Customer not found.')
        return redirect('customers:index')
    customer['segment'] = _segment(customer.get('visit_count', 0), customer.get('total_spend', 0))
    # Recent orders for this customer by name match
    orders = list(col.orders().find(
        {'business_id': bid, 'customer_name': customer.get('name', '')},
        sort=[('created_at', -1)], limit=10
    ))
    return render(request, 'customers/detail.html', {
        'business': business,
        'customer': customer,
        'orders': orders,
    })
