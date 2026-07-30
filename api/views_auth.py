from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import User, Business, Membership, SubscriptionPlan, BusinessSubscription, LoginHistory
from .serializers import (
    RegisterSerializer, UserSerializer, UserUpdateSerializer, BusinessSerializer,
    MembershipSerializer, LoginHistorySerializer,
)
from .tenancy import get_active_membership, require_manager


def _client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR')


class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = TokenObtainPairSerializer.get_token(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    Email + password → JWT pair.

    simplejwt's stock view authenticates on ``USERNAME_FIELD``, which is still
    ``username`` on this User model — so it can't take an email payload directly.
    This app mirrors ``username`` from the email at registration, so we resolve
    the user by email first and authenticate with their real username. Also
    records LoginHistory, matching the old session-based login view.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = str(request.data.get('email') or request.data.get('username') or '').strip()
        password = request.data.get('password') or ''
        if not email or not password:
            return Response({'error': 'Email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Prefer an exact email match; fall back to treating the input as a
        # username so pre-existing accounts still work.
        candidate = User.objects.filter(email__iexact=email).first()
        login_name = candidate.username if candidate else email
        user = authenticate(request, username=login_name, password=password)

        if user is None:
            if candidate:
                LoginHistory.objects.create(
                    user=candidate, ip_address=_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''), success=False,
                )
            return Response({'error': 'Invalid email or password.'}, status=status.HTTP_401_UNAUTHORIZED)

        LoginHistory.objects.create(
            user=user, ip_address=_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''), success=True,
        )
        refresh = TokenObtainPairSerializer.get_token(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })


class MeView(APIView):
    """GET current user + active business/membership context; PATCH account fields."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        membership = get_active_membership(request)
        memberships = Membership.objects.filter(user=request.user, is_active=True).select_related('business')
        return Response({
            'user': UserSerializer(request.user).data,
            'active_membership': MembershipSerializer(membership).data if membership else None,
            'memberships': MembershipSerializer(memberships, many=True).data,
        })

    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class LoginHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LoginHistorySerializer
    # Already capped at 10 — returning a bare list keeps the client simple.
    pagination_class = None

    def get_queryset(self):
        return self.request.user.login_history.all()[:10]


class BusinessListCreateView(APIView):
    """List the user's businesses (via memberships), or create a new one (becomes owner)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = Membership.objects.filter(user=request.user, is_active=True).select_related('business')
        return Response(MembershipSerializer(memberships, many=True).data)

    def post(self, request):
        serializer = BusinessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        business = serializer.save()
        Membership.objects.create(user=request.user, business=business, role='owner')
        plan, _ = SubscriptionPlan.objects.get_or_create(
            name='basic',
            defaults={
                'display_name': 'Basic', 'price_monthly': 2999,
                'max_users': 3, 'max_menu_items': 50, 'ai_features': False,
            },
        )
        BusinessSubscription.objects.create(business=business, plan=plan, status='trial')
        return Response(BusinessSerializer(business).data, status=status.HTTP_201_CREATED)


class BusinessDetailView(APIView):
    """Retrieve or update (manager/owner only) a business's profile fields."""
    permission_classes = [IsAuthenticated]

    def _get(self, request, business_id):
        membership = get_object_or_404(Membership, user=request.user, business_id=business_id, is_active=True)
        return membership

    def get(self, request, business_id):
        membership = self._get(request, business_id)
        return Response(BusinessSerializer(membership.business).data)

    def patch(self, request, business_id):
        membership = self._get(request, business_id)
        require_manager(membership)
        serializer = BusinessSerializer(membership.business, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class BusinessActivateView(APIView):
    """
    Validates the user belongs to this business (kept for parity with the old
    session-based switch_business_view). The React client should store the
    returned business_id and send it as X-Business-Id on subsequent requests —
    there is no server-side session to update for a stateless JWT API.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, business_id):
        membership = get_object_or_404(Membership, user=request.user, business_id=business_id, is_active=True)
        return Response(MembershipSerializer(membership).data)
