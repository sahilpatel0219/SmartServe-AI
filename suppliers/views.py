from datetime import datetime, timezone
from bson import ObjectId
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Membership
from mongo import collections as col


def _get_business(request):
    from core.utils import get_active_business
    return get_active_business(request)


@login_required
def index_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    sups = list(col.suppliers().find({'business_id': business.mongo_id}, sort=[('name', 1)]))
    for s in sups:
        s['str_id'] = str(s['_id'])
    return render(request, 'suppliers/index.html', {'business': business, 'suppliers': sups})


@login_required
def add_supplier_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Supplier name is required.')
        else:
            col.suppliers().insert_one({
                'business_id': business.mongo_id,
                'name': name,
                'contact_person': request.POST.get('contact_person', '').strip(),
                'phone': request.POST.get('phone', '').strip(),
                'email': request.POST.get('email', '').strip(),
                'address': request.POST.get('address', '').strip(),
                'products': request.POST.get('products', '').strip(),
                'payment_terms': request.POST.get('payment_terms', '').strip(),
                'created_at': datetime.now(timezone.utc),
            })
            messages.success(request, f'Supplier "{name}" added.')
            return redirect('suppliers:index')
    return render(request, 'suppliers/add.html', {'business': business})


@login_required
def edit_supplier_view(request, supplier_id):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    supplier = col.suppliers().find_one({'_id': ObjectId(supplier_id), 'business_id': bid})
    if not supplier:
        messages.error(request, 'Supplier not found.')
        return redirect('suppliers:index')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Supplier name is required.')
        else:
            col.suppliers().update_one(
                {'_id': ObjectId(supplier_id)},
                {'$set': {
                    'name': name,
                    'contact_person': request.POST.get('contact_person', '').strip(),
                    'phone': request.POST.get('phone', '').strip(),
                    'email': request.POST.get('email', '').strip(),
                    'address': request.POST.get('address', '').strip(),
                    'products': request.POST.get('products', '').strip(),
                    'payment_terms': request.POST.get('payment_terms', '').strip(),
                    'updated_at': datetime.now(timezone.utc),
                }},
            )
            messages.success(request, f'Supplier "{name}" updated.')
            return redirect('suppliers:index')
    supplier['str_id'] = str(supplier['_id'])
    return render(request, 'suppliers/edit.html', {'business': business, 'supplier': supplier})


@login_required
def delete_supplier_view(request, supplier_id):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    col.suppliers().delete_one({'_id': ObjectId(supplier_id), 'business_id': business.mongo_id})
    messages.success(request, 'Supplier removed.')
    return redirect('suppliers:index')


@login_required
def purchase_order_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    sups = list(col.suppliers().find({'business_id': bid}, {'name': 1}))
    for s in sups:
        s['str_id'] = str(s['_id'])
    pos = list(col.purchase_orders().find({'business_id': bid}, sort=[('created_at', -1)], limit=50))
    for p in pos:
        p['str_id'] = str(p['_id'])
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier_id', '')
        supplier_name = request.POST.get('supplier_name', '')
        items_raw = request.POST.get('items', '').strip()
        total = float(request.POST.get('total', 0) or 0)
        col.purchase_orders().insert_one({
            'business_id': bid,
            'supplier_id': supplier_id,
            'supplier_name': supplier_name,
            'items': items_raw,
            'total_amount': total,
            'status': 'pending',
            'created_at': datetime.now(timezone.utc),
        })
        messages.success(request, 'Purchase order created.')
        return redirect('suppliers:purchase_orders')
    return render(request, 'suppliers/purchase_orders.html', {
        'business': business,
        'suppliers': sups,
        'purchase_orders': pos,
    })
