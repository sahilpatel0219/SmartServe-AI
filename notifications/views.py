"""
Notifications: generates smart alerts from real business data (low stock, expiry,
forecast anomalies) and persists them in MongoDB.
"""
from datetime import datetime, timezone

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from accounts.models import Membership
from mongo import collections as col


def _get_business(request):
    m = Membership.objects.filter(user=request.user, is_active=True).select_related('business').first()
    return (m.business, m) if m else (None, None)


def generate_notifications(bid: str):
    """
    Scan inventory and latest prediction for alert conditions.
    Inserts new notifications; avoids exact duplicates within 24 h.
    """
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    cutoff_24h = now - timedelta(hours=24)
    existing = {
        n['message']
        for n in col.notifications().find({
            'business_id': bid,
            'created_at': {'$gte': cutoff_24h},
        })
    }

    new_notifs = []

    # ── Inventory alerts ──────────────────────────────────────────────────────
    import pandas as pd
    inv = list(col.inventory().find({'business_id': bid}))
    for item in inv:
        name = item.get('item_name', 'Unknown')
        try:
            qty = float(str(item.get('quantity', 0)).replace(',', ''))
            reorder = float(str(item.get('reorder_level', 0)).replace(',', ''))
        except ValueError:
            continue

        if qty <= reorder:
            msg = f"Low stock: {name} is at {qty} {item.get('unit','units')} (reorder level: {reorder})"
            if msg not in existing:
                new_notifs.append({'type': 'low_stock', 'severity': 'warning', 'message': msg})

        exp = item.get('expiry_date', '')
        if exp:
            try:
                exp_dt = pd.to_datetime(str(exp))
                days_left = (exp_dt - pd.Timestamp.now()).days
                if 0 <= days_left <= 3:
                    msg = f"Expiry alert: {name} expires in {days_left} day(s)."
                    if msg not in existing:
                        new_notifs.append({'type': 'expiry', 'severity': 'danger', 'message': msg})
                elif days_left < 0:
                    msg = f"Expired: {name} expired {abs(days_left)} day(s) ago."
                    if msg not in existing:
                        new_notifs.append({'type': 'expired', 'severity': 'danger', 'message': msg})
            except Exception:
                pass

    # ── AI forecast alerts ────────────────────────────────────────────────────
    pred = col.predictions().find_one({'business_id': bid}, sort=[('created_at', -1)])
    if pred:
        waste = pred.get('waste', {}).get('estimated_loss_inr', 0)
        if waste and float(waste) > 500:
            msg = f"Waste risk: estimated ₹{float(waste):,.0f} in potential food waste. Review inventory."
            if msg not in existing:
                new_notifs.append({'type': 'waste_risk', 'severity': 'warning', 'message': msg})

        hs = pred.get('health_score', {}).get('total_score', None)
        if hs is not None and float(hs) < 40:
            msg = f"Health score alert: your business health score is {float(hs):.1f}/100. Review AI insights."
            if msg not in existing:
                new_notifs.append({'type': 'health_score', 'severity': 'danger', 'message': msg})

    # Insert new notifications
    for n in new_notifs:
        n.update({'business_id': bid, 'read': False, 'created_at': now})
    if new_notifs:
        col.notifications().insert_many(new_notifs)

    return len(new_notifs)


@login_required
def index_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id

    # Auto-generate fresh alerts on page load
    generate_notifications(bid)

    notifs = list(col.notifications().find({'business_id': bid}, sort=[('created_at', -1)], limit=50))
    for n in notifs:
        n['str_id'] = str(n.get('_id', ''))
    unread = sum(1 for n in notifs if not n.get('read'))

    return render(request, 'notifications/index.html', {
        'business': business,
        'notifications': notifs,
        'unread': unread,
    })


@login_required
@require_POST
def mark_read_view(request, notif_id):
    business, _ = _get_business(request)
    if not business:
        return JsonResponse({'error': 'No business'}, status=403)
    from bson import ObjectId
    try:
        col.notifications().update_one(
            {'_id': ObjectId(notif_id), 'business_id': business.mongo_id},
            {'$set': {'read': True}}
        )
    except Exception:
        pass
    return JsonResponse({'ok': True})


@login_required
@require_POST
def mark_all_read_view(request):
    business, _ = _get_business(request)
    if not business:
        return JsonResponse({'error': 'No business'}, status=403)
    col.notifications().update_many(
        {'business_id': business.mongo_id, 'read': False},
        {'$set': {'read': True}}
    )
    return JsonResponse({'ok': True})
