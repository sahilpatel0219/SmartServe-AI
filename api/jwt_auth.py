"""
Manual JWT authentication for plain Django views (e.g. binary file-download
endpoints) that can't cleanly return a DRF Response — see api/views_reports.py.
"""
from django.http import HttpResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from accounts.models import Membership


def authenticate_request(request):
    """Returns the authenticated User, or None. Accepts either a JWT bearer
    token or an existing Django session (parity with DRF's dual-auth setup)."""
    if request.user.is_authenticated:
        return request.user
    try:
        result = JWTAuthentication().authenticate(request)
    except Exception:
        return None
    if result is None:
        return None
    user, _token = result
    return user


def resolve_business_for_user(request, user):
    """Same precedence as api.tenancy.get_active_business, for a plain HttpRequest."""
    qs = Membership.objects.filter(user=user, is_active=True).select_related('business')
    requested_id = request.headers.get('X-Business-Id') or request.GET.get('business_id')
    membership = qs.filter(business_id=requested_id).first() if requested_id else qs.first()
    return (membership.business, membership) if membership else (None, None)


def require_authenticated_business(view_func):
    """Decorator for plain Django views: 401s or 403s before reaching the view body."""
    def wrapper(request, *args, **kwargs):
        user = authenticate_request(request)
        if not user:
            return HttpResponse('Authentication required.', status=401)
        business, membership = resolve_business_for_user(request, user)
        if not business:
            return HttpResponse('No active business workspace for this user.', status=403)
        request.api_business = business
        request.api_membership = membership
        return view_func(request, *args, **kwargs)
    return wrapper
