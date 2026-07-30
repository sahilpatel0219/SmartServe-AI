"""
Tenant resolution for the stateless JWT API.

Template-era views resolved the "active business" from a Django session key
(``core.utils.get_active_business``). A JWT API call carries no session, so the
same business must be resolved per-request from an explicit ``business_id``
(header or query param), falling back to the user's first active membership.
The resolved business is NEVER trusted from arbitrary client input beyond this
lookup — it is always re-validated against a real, active ``Membership`` row.
"""
from rest_framework.exceptions import PermissionDenied
from accounts.models import Membership


def get_active_membership(request):
    """
    Resolve the caller's active Membership.

    Precedence: ``X-Business-Id`` header -> ``business_id`` query param ->
    user's first active membership. Returns None if the user has no active
    membership, or if an explicit business_id was given but doesn't belong
    to the user.
    """
    qs = Membership.objects.filter(user=request.user, is_active=True).select_related('business')

    requested_id = request.headers.get('X-Business-Id') or request.query_params.get('business_id')
    if requested_id:
        return qs.filter(business_id=requested_id).first()

    return qs.first()


def get_active_business(request):
    """Convenience wrapper returning ``(business, membership)`` or ``(None, None)``."""
    m = get_active_membership(request)
    return (m.business, m) if m else (None, None)


def require_business(request):
    """Like get_active_business, but raises a DRF-friendly 403 if none found."""
    business, membership = get_active_business(request)
    if not business:
        raise PermissionDenied('No active business workspace for this user.')
    return business, membership


def require_manager(membership):
    if not membership or not membership.is_manager:
        raise PermissionDenied('Only the owner or a manager can perform this action.')
