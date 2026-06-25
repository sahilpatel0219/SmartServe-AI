"""
Injects the active business workspace + membership into every template context.
"""
from accounts.models import Business, Membership


def global_context(request):
    ctx = {
        'active_business': None,
        'active_membership': None,
        'user_businesses': [],
        'app_name': 'SmartServe AI',
    }

    if not request.user.is_authenticated:
        return ctx

    memberships = Membership.objects.filter(
        user=request.user, is_active=True
    ).select_related('business')

    ctx['user_businesses'] = [m.business for m in memberships]

    # Determine active business: prefer session value, else first membership
    active_id = request.session.get('active_business_id')
    if active_id:
        active = next((m for m in memberships if m.business_id == int(active_id)), None)
        if active:
            ctx['active_business'] = active.business
            ctx['active_membership'] = active
            return ctx

    if memberships:
        first = memberships[0]
        ctx['active_business'] = first.business
        ctx['active_membership'] = first
        request.session['active_business_id'] = first.business_id

    return ctx
