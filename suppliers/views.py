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
    sups = list(col.suppliers().find({'business_id': bid}))
    return render(request, 'suppliers/index.html', {'business': membership.business, 'suppliers': sups})
