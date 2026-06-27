from datetime import datetime, timezone
from bson import ObjectId
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from accounts.models import Membership
from mongo import collections as col

STATUSES = ['pending', 'preparing', 'ready', 'delivered', 'cancelled']

def _get_business(request):
    m = Membership.objects.filter(user=request.user, is_active=True).select_related('business').first()
    return (m.business, m) if m else (None, None)


@login_required
def index_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    status_filter = request.GET.get('status', '')
    query = {'business_id': bid}
    if status_filter:
        query['status'] = status_filter
    orders = list(col.orders().find(query, sort=[('created_at', -1)], limit=100))
    for o in orders:
        o['str_id'] = str(o.get('_id', ''))
    counts = {s: col.orders().count_documents({'business_id': bid, 'status': s}) for s in STATUSES}
    statuses_with_counts = [(s, counts[s]) for s in STATUSES]
    return render(request, 'orders/index.html', {
        'business': business,
        'orders': orders,
        'statuses': STATUSES,
        'statuses_with_counts': statuses_with_counts,
        'status_filter': status_filter,
        'counts': counts,
    })


@login_required
def create_order_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    menu_items = list(col.menu_items().find({'business_id': bid, 'is_available': True}, sort=[('category', 1), ('name', 1)]))
    for mi in menu_items:
        mi['str_id'] = str(mi['_id'])
    if request.method == 'POST':
        order_type = request.POST.get('order_type', 'dine_in')
        table_no = request.POST.get('table_no', '').strip()
        customer_name = request.POST.get('customer_name', '').strip()
        notes = request.POST.get('notes', '').strip()
        item_ids = request.POST.getlist('item_id')
        item_qtys = request.POST.getlist('item_qty')
        line_items = []
        total = 0.0
        for iid, qty_str in zip(item_ids, item_qtys):
            qty = int(qty_str or 0)
            if qty <= 0:
                continue
            menu_item = col.menu_items().find_one({'_id': ObjectId(iid), 'business_id': bid})
            if menu_item:
                subtotal = menu_item.get('price', 0) * qty
                total += subtotal
                line_items.append({
                    'item_id': iid,
                    'name': menu_item.get('name', ''),
                    'price': menu_item.get('price', 0),
                    'quantity': qty,
                    'subtotal': subtotal,
                    'recipe': menu_item.get('recipe', []),
                })
        if not line_items:
            messages.error(request, 'Add at least one item to the order.')
        else:
            order = {
                'business_id': bid,
                'order_type': order_type,
                'table_no': table_no,
                'customer_name': customer_name,
                'notes': notes,
                'items': line_items,
                'total_amount': round(total, 2),
                'status': 'pending',
                'created_at': datetime.now(timezone.utc),
            }
            result = col.orders().insert_one(order)
            # Auto-deduct inventory based on recipe mappings
            _deduct_inventory(bid, line_items)
            messages.success(request, f'Order #{str(result.inserted_id)[-6:].upper()} created.')
            return redirect('orders:index')
    return render(request, 'orders/create.html', {
        'business': business,
        'menu_items': menu_items,
        'order_types': [('dine_in', 'Dine In'), ('takeaway', 'Takeaway'), ('delivery', 'Delivery'), ('qr', 'QR Order'), ('phone', 'Phone')],
    })


def _deduct_inventory(business_id, line_items):
    """Deduct ingredients from inventory based on each ordered item's recipe."""
    for line in line_items:
        for ing in line.get('recipe', []):
            name = ing.get('ingredient', '')
            qty_to_deduct = ing.get('quantity', 0) * line['quantity']
            if name and qty_to_deduct > 0:
                col.inventory().update_one(
                    {'business_id': business_id, 'item_name': name},
                    {'$inc': {'quantity': -qty_to_deduct}},
                )


@login_required
def update_status_view(request, order_id):
    business, _ = _get_business(request)
    if not business:
        return JsonResponse({'error': 'No business'}, status=400)
    new_status = request.POST.get('status', '')
    if new_status not in STATUSES:
        return JsonResponse({'error': 'Invalid status'}, status=400)
    col.orders().update_one(
        {'_id': ObjectId(order_id), 'business_id': business.mongo_id},
        {'$set': {'status': new_status, 'updated_at': datetime.now(timezone.utc)}}
    )
    return JsonResponse({'status': new_status})


@login_required
def detail_view(request, order_id):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    order = col.orders().find_one({'_id': ObjectId(order_id), 'business_id': business.mongo_id})
    if not order:
        messages.error(request, 'Order not found.')
        return redirect('orders:index')
    order['str_id'] = str(order['_id'])
    order['short_id'] = str(order['_id'])[-6:].upper()
    return render(request, 'orders/detail.html', {'business': business, 'order': order, 'statuses': STATUSES})
