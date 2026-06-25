from datetime import datetime, timezone, date
from bson import ObjectId
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
    items = list(col.inventory().find({'business_id': bid}, sort=[('item_name', 1)]))
    today = date.today()
    for item in items:
        qty = float(str(item.get('quantity', 0)).replace(',', '') or 0)
        reorder = float(str(item.get('reorder_level', 0)).replace(',', '') or 0)
        item['low_stock'] = qty <= reorder
        exp = item.get('expiry_date', '')
        if exp:
            try:
                import pandas as pd
                exp_date = pd.to_datetime(str(exp)).date()
                item['days_to_expiry'] = (exp_date - today).days
                item['expiring_soon'] = item['days_to_expiry'] <= 7
            except Exception:
                item['days_to_expiry'] = None
                item['expiring_soon'] = False
        else:
            item['days_to_expiry'] = None
            item['expiring_soon'] = False
    low_stock_count = sum(1 for i in items if i['low_stock'])
    expiring_count = sum(1 for i in items if i['expiring_soon'])
    return render(request, 'inventory/index.html', {
        'business': business,
        'items': items,
        'low_stock_count': low_stock_count,
        'expiring_count': expiring_count,
    })


@login_required
def add_stock_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    if request.method == 'POST':
        item_name = request.POST.get('item_name', '').strip()
        if not item_name:
            messages.error(request, 'Item name is required.')
        else:
            doc = {
                'business_id': bid,
                'item_name': item_name,
                'quantity': float(request.POST.get('quantity', 0) or 0),
                'unit': request.POST.get('unit', '').strip(),
                'cost_per_unit': float(request.POST.get('cost_per_unit', 0) or 0),
                'reorder_level': float(request.POST.get('reorder_level', 0) or 0),
                'expiry_date': request.POST.get('expiry_date', '').strip() or None,
                'category': request.POST.get('category', '').strip(),
                'supplier': request.POST.get('supplier', '').strip(),
                'created_at': datetime.now(timezone.utc),
            }
            # Update if same item exists, else insert
            existing = col.inventory().find_one({'business_id': bid, 'item_name': item_name})
            if existing:
                col.inventory().update_one({'_id': existing['_id']}, {'$set': doc})
                messages.success(request, f'"{item_name}" stock updated.')
            else:
                col.inventory().insert_one(doc)
                messages.success(request, f'"{item_name}" added to inventory.')
            return redirect('inventory:index')
    return render(request, 'inventory/add_stock.html', {'business': business})


@login_required
def edit_stock_view(request, item_id):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    item = col.inventory().find_one({'_id': ObjectId(item_id), 'business_id': bid})
    if not item:
        messages.error(request, 'Item not found.')
        return redirect('inventory:index')
    if request.method == 'POST':
        updates = {
            'item_name': request.POST.get('item_name', '').strip(),
            'quantity': float(request.POST.get('quantity', 0) or 0),
            'unit': request.POST.get('unit', '').strip(),
            'cost_per_unit': float(request.POST.get('cost_per_unit', 0) or 0),
            'reorder_level': float(request.POST.get('reorder_level', 0) or 0),
            'expiry_date': request.POST.get('expiry_date', '').strip() or None,
            'category': request.POST.get('category', '').strip(),
            'updated_at': datetime.now(timezone.utc),
        }
        col.inventory().update_one({'_id': ObjectId(item_id)}, {'$set': updates})
        messages.success(request, 'Inventory item updated.')
        return redirect('inventory:index')
    return render(request, 'inventory/edit_stock.html', {'business': business, 'item': item})


@login_required
def delete_stock_view(request, item_id):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    col.inventory().delete_one({'_id': ObjectId(item_id), 'business_id': business.mongo_id})
    messages.success(request, 'Item removed from inventory.')
    return redirect('inventory:index')
