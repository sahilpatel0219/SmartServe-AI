from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.models import Membership

@login_required
def index_view(request):
    membership = Membership.objects.filter(user=request.user, is_active=True).select_related('business').first()
    if not membership:
        return redirect('onboarding:create_business')
    from mongo import collections as col
    bid = membership.business.mongo_id
    items = list(col.menu_items().find({'business_id': bid}, sort=[('name', 1)]))
    return render(request, 'catalog/index.html', {'business': membership.business, 'items': items})

@login_required
def create_item_view(request):
    membership = Membership.objects.filter(user=request.user, is_active=True).select_related('business').first()
    if not membership:
        return redirect('onboarding:create_business')
    return render(request, 'catalog/create_item.html', {'business': membership.business})
