import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Business, Membership, SubscriptionPlan, BusinessSubscription
from accounts.forms import BusinessForm


@login_required
def create_business_view(request):
    """Step 1 of onboarding: register a new business workspace."""
    if request.user.memberships.filter(is_active=True).exists():
        if request.GET.get('new') != '1':
            return redirect('onboarding:upload_center')

    form = BusinessForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        business = form.save()
        Membership.objects.create(user=request.user, business=business, role='owner')
        plan, _ = SubscriptionPlan.objects.get_or_create(
            name='basic',
            defaults={
                'display_name': 'Basic',
                'price_monthly': 2999,
                'max_users': 3,
                'max_menu_items': 50,
                'ai_features': False,
            }
        )
        BusinessSubscription.objects.create(business=business, plan=plan, status='trial')
        request.session['active_business_id'] = business.pk
        messages.success(request, f'"{business.name}" workspace created! Now upload your business data to unlock AI features.')
        return redirect('onboarding:upload_center')

    return render(request, 'onboarding/create_business.html', {'form': form})


@login_required
def upload_center_view(request):
    """Data Import Center — hub for all data uploads."""
    membership = Membership.objects.filter(
        user=request.user, is_active=True
    ).select_related('business').first()
    if not membership:
        return redirect('onboarding:create_business')

    business = membership.business
    from mongo import collections as col
    bid = business.mongo_id

    datasets = list(col.uploaded_datasets().find(
        {'business_id': bid},
        {'type': 1, 'filename': 1, 'row_count': 1, 'uploaded_at': 1, 'status': 1},
        sort=[('uploaded_at', -1)]
    ))

    has_sales = any(d['type'] == 'sales' for d in datasets)
    has_inventory = any(d['type'] == 'inventory' for d in datasets)
    has_menu = any(d['type'] == 'menu' for d in datasets)
    has_orders = any(d['type'] == 'orders' for d in datasets)

    upload_types = [
        {
            'key': 'sales',
            'label': 'Sales History',
            'icon': 'currency-rupee',
            'done': has_sales,
            'desc': 'Date, item, quantity, revenue. Required for AI forecasting.',
            'columns': 'date, item_name, quantity, revenue, cost (optional)',
        },
        {
            'key': 'inventory',
            'label': 'Inventory',
            'icon': 'box-seam',
            'done': has_inventory,
            'desc': 'Current stock levels, units, costs, expiry dates.',
            'columns': 'item_name, quantity, unit, cost_per_unit, reorder_level, expiry_date (optional)',
        },
        {
            'key': 'menu',
            'label': 'Menu',
            'icon': 'journal-text',
            'done': has_menu,
            'desc': 'Menu items with prices. Enables profitability analytics.',
            'columns': 'item_name, category, price, cost, is_available',
        },
        {
            'key': 'orders',
            'label': 'Historical Orders',
            'icon': 'receipt',
            'done': has_orders,
            'desc': 'Past order records for demand analysis.',
            'columns': 'order_date, order_id, item_name, quantity, amount, order_type',
        },
    ]

    done_count = sum(1 for t in upload_types if t['done'])
    readiness_score = int((done_count / len(upload_types)) * 100)

    return render(request, 'onboarding/upload_center.html', {
        'business': business,
        'upload_types': upload_types,
        'datasets': datasets,
        'readiness_score': readiness_score,
        'done_count': done_count,
    })


@login_required
def upload_file_view(request, upload_type):
    """Handle file upload → validate → show preview → confirm → commit."""
    membership = Membership.objects.filter(
        user=request.user, is_active=True
    ).select_related('business').first()
    if not membership:
        return redirect('onboarding:create_business')

    business = membership.business
    VALID_TYPES = {'sales', 'inventory', 'menu', 'orders'}
    if upload_type not in VALID_TYPES:
        messages.error(request, 'Invalid upload type.')
        return redirect('onboarding:upload_center')

    if request.method == 'POST':
        # ── Confirm step: records are stored in session ──────────────────────
        if request.POST.get('confirm') == '1':
            session_key = f'upload_preview_{upload_type}'
            payload = request.session.get(session_key)
            if not payload:
                messages.error(request, 'Preview session expired. Please re-upload the file.')
                return redirect('onboarding:upload_center')

            from .services import commit_upload
            commit_upload(
                payload['records'], upload_type,
                business.mongo_id, payload['filename'], payload['row_count']
            )
            del request.session[session_key]
            messages.success(request, f'{payload["row_count"]} rows imported successfully!')
            return redirect('onboarding:upload_center')

        # ── Upload step: parse & validate the file ───────────────────────────
        from .services import validate_and_preview
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            messages.error(request, 'Please select a file to upload.')
            return redirect('onboarding:upload_center')

        result = validate_and_preview(uploaded_file, upload_type)

        if result['status'] == 'error':
            messages.error(request, result['message'])
            return redirect('onboarding:upload_center')

        # Store records in session so confirmation doesn't need the file again.
        # Records are plain dicts of strings (from pandas) — safe to serialise.
        session_key = f'upload_preview_{upload_type}'
        # Limit session size: only store up to 5 000 rows in session;
        # larger uploads are committed directly without a preview step.
        MAX_SESSION_ROWS = 5000
        if result['row_count'] <= MAX_SESSION_ROWS:
            request.session[session_key] = {
                'records': result['records'],
                'filename': uploaded_file.name,
                'row_count': result['row_count'],
            }
            return render(request, 'onboarding/upload_preview.html', {
                'business': business,
                'upload_type': upload_type,
                'result': result,
            })
        else:
            # Large file: commit immediately and skip preview
            from .services import commit_upload
            commit_upload(result['records'], upload_type,
                          business.mongo_id, uploaded_file.name, result['row_count'])
            messages.success(request, f'{result["row_count"]} rows imported successfully!')
            return redirect('onboarding:upload_center')

    return redirect('onboarding:upload_center')


@login_required
def download_template_view(request, upload_type):
    """Return a downloadable CSV template for the given upload type."""
    from .services import generate_template_csv
    return generate_template_csv(upload_type)
