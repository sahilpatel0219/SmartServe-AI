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
    orders = list(col.orders().find({'business_id': bid}, sort=[('created_at', -1)], limit=50))
    return render(request, 'orders/index.html', {'business': membership.business, 'orders': orders})

@login_required
def create_order_view(request):
    membership = Membership.objects.filter(user=request.user, is_active=True).select_related('business').first()
    if not membership:
        return redirect('onboarding:create_business')
    return render(request, 'orders/create.html', {'business': membership.business})
