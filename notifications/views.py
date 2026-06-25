from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.models import Membership

@login_required
def index_view(request):
    membership = Membership.objects.filter(user=request.user, is_active=True).select_related('business').first()
    if not membership:
        return redirect('onboarding:create_business')
    business = membership.business
    from mongo import collections as col
    bid = business.mongo_id
    notifs = list(col.notifications().find({'business_id': bid}, sort=[('created_at', -1)], limit=50))
    return render(request, 'notifications/index.html', {'business': business, 'notifications': notifs})
