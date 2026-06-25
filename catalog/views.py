import json
from datetime import datetime, timezone
from bson import ObjectId
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from accounts.models import Membership
from mongo import collections as col


def _get_business(request):
    m = Membership.objects.filter(user=request.user, is_active=True).select_related('business').first()
    return (m.business, m) if m else (None, None)


@login_required
def index_view(request):
    business, membership = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    category_filter = request.GET.get('category', '')
    query = {'business_id': bid}
    if category_filter:
        query['category'] = category_filter
    items = list(col.menu_items().find(query, sort=[('category', 1), ('name', 1)]))
    categories = col.menu_items().distinct('category', {'business_id': bid})
    return render(request, 'catalog/index.html', {
        'business': business,
        'items': items,
        'categories': sorted(categories),
        'category_filter': category_filter,
    })


@login_required
def create_item_view(request):
    business, membership = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    categories = col.menu_items().distinct('category', {'business_id': bid})
    inv_items = list(col.inventory().find({'business_id': bid}, {'item_name': 1, 'unit': 1}))
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category = request.POST.get('category', '').strip()
        new_cat = request.POST.get('new_category', '').strip()
        if new_cat:
            category = new_cat
        price = float(request.POST.get('price', 0) or 0)
        cost = float(request.POST.get('cost', 0) or 0)
        description = request.POST.get('description', '').strip()
        is_available = request.POST.get('is_available') == 'on'
        recipe = []
        for n, q, u in zip(
            request.POST.getlist('ingredient_name'),
            request.POST.getlist('ingredient_qty'),
            request.POST.getlist('ingredient_unit'),
        ):
            if n.strip():
                recipe.append({'ingredient': n.strip(), 'quantity': float(q or 0), 'unit': u.strip()})
        if not name:
            messages.error(request, 'Item name is required.')
        else:
            col.menu_items().insert_one({
                'business_id': bid,
                'name': name,
                'category': category,
                'price': price,
                'cost': cost,
                'description': description,
                'is_available': is_available,
                'recipe': recipe,
                'created_at': datetime.now(timezone.utc),
            })
            messages.success(request, f'"{name}" added to menu.')
            return redirect('catalog:index')
    return render(request, 'catalog/create_item.html', {
        'business': business,
        'categories': sorted(categories),
        'inv_items': inv_items,
    })


@login_required
def edit_item_view(request, item_id):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    item = col.menu_items().find_one({'_id': ObjectId(item_id), 'business_id': bid})
    if not item:
        messages.error(request, 'Item not found.')
        return redirect('catalog:index')
    categories = col.menu_items().distinct('category', {'business_id': bid})
    inv_items = list(col.inventory().find({'business_id': bid}, {'item_name': 1, 'unit': 1}))
    if request.method == 'POST':
        category = request.POST.get('category', '').strip()
        new_cat = request.POST.get('new_category', '').strip()
        if new_cat:
            category = new_cat
        recipe = []
        for n, q, u in zip(
            request.POST.getlist('ingredient_name'),
            request.POST.getlist('ingredient_qty'),
            request.POST.getlist('ingredient_unit'),
        ):
            if n.strip():
                recipe.append({'ingredient': n.strip(), 'quantity': float(q or 0), 'unit': u.strip()})
        updates = {
            'name': request.POST.get('name', '').strip(),
            'category': category,
            'price': float(request.POST.get('price', 0) or 0),
            'cost': float(request.POST.get('cost', 0) or 0),
            'description': request.POST.get('description', '').strip(),
            'is_available': request.POST.get('is_available') == 'on',
            'recipe': recipe,
            'updated_at': datetime.now(timezone.utc),
        }
        col.menu_items().update_one({'_id': ObjectId(item_id)}, {'$set': updates})
        messages.success(request, 'Item updated.')
        return redirect('catalog:index')
    return render(request, 'catalog/edit_item.html', {
        'business': business,
        'item': item,
        'categories': sorted(categories),
        'inv_items': inv_items,
    })


@login_required
def delete_item_view(request, item_id):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    col.menu_items().delete_one({'_id': ObjectId(item_id), 'business_id': business.mongo_id})
    messages.success(request, 'Item deleted.')
    return redirect('catalog:index')
