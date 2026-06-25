import secrets
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .forms import RegisterForm, LoginForm, BusinessForm
from .models import User, Business, Membership, SubscriptionPlan, BusinessSubscription, LoginHistory


def _get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.email_verification_token = secrets.token_hex(32)
        user.save()
        # Auto-login after register; email verification prints to console in dev
        login(request, user)
        messages.success(request, f'Welcome to SmartServe AI, {user.first_name}! Let\'s set up your business.')
        return redirect('onboarding:create_business')

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            LoginHistory.objects.create(
                user=user,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True,
            )
            next_url = request.GET.get('next', '')
            return redirect(next_url if next_url else 'core:dashboard')
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def profile_view(request):
    membership = request.user.memberships.filter(is_active=True).first()
    return render(request, 'accounts/profile.html', {
        'membership': membership,
        'login_history': request.user.login_history.all()[:10],
    })


@login_required
def switch_business_view(request, business_id):
    """Allow a user to switch active workspace if they belong to multiple businesses."""
    membership = get_object_or_404(
        Membership, user=request.user, business_id=business_id, is_active=True
    )
    request.session['active_business_id'] = business_id
    return redirect('core:dashboard')
