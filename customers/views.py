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
    custs = list(col.customers().find({'business_id': bid}, sort=[('name', 1)]))
    return render(request, 'customers/index.html', {'business': membership.business, 'customers': custs})

@login_required
def add_customer_view(request):
    membership = Membership.objects.filter(user=request.user, is_active=True).select_related('business').first()
    if not membership:
        return redirect('onboarding:create_business')
    return render(request, 'customers/add.html', {'business': membership.business})
