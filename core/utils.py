"""Shared helpers for resolving the user's active business workspace."""
from accounts.models import Membership


def get_active_membership(request):
    """
    Return the Membership for the user's *active* business.

    Honours the session's active_business_id (set when switching workspaces or
    creating one) so every page shows the same business as the sidebar/topbar.
    Falls back to the first active membership.
    """
    qs = Membership.objects.filter(
        user=request.user, is_active=True
    ).select_related('business')

    active_id = request.session.get('active_business_id')
    membership = None
    if active_id:
        membership = qs.filter(business_id=active_id).first()
    if membership is None:
        membership = qs.first()
    return membership


def get_active_business(request):
    """Convenience wrapper returning ``(business, membership)`` or ``(None, None)``."""
    m = get_active_membership(request)
    return (m.business, m) if m else (None, None)
