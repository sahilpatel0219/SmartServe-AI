import uuid

from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from mongo import collections as col
from onboarding.services import validate_and_preview, commit_upload, generate_template_csv
from .tenancy import require_business

VALID_TYPES = {'sales', 'inventory', 'menu', 'orders', 'customers'}
MAX_PREVIEW_ROWS = 5000
UPLOAD_CACHE_TTL = 600  # seconds — matches how long a preview should stay confirmable


class UploadCenterView(APIView):
    """Data readiness hub — which upload types have data, plus recent uploaded_datasets."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business, _ = require_business(request)
        bid = business.mongo_id

        datasets = list(col.uploaded_datasets().find(
            {'business_id': bid},
            {'type': 1, 'filename': 1, 'row_count': 1, 'uploaded_at': 1, 'status': 1},
            sort=[('uploaded_at', -1)],
        ))
        for d in datasets:
            d['_id'] = str(d['_id'])

        done = {t: any(d['type'] == t for d in datasets) for t in VALID_TYPES}
        upload_types = [
            {'key': 'sales', 'label': 'Sales History', 'done': done['sales'],
             'desc': 'Date, item, quantity, revenue. Required for AI forecasting.',
             'columns': 'date, item_name, quantity, revenue, cost (optional)'},
            {'key': 'inventory', 'label': 'Inventory', 'done': done['inventory'],
             'desc': 'Current stock levels, units, costs, expiry dates.',
             'columns': 'item_name, quantity, unit, cost_per_unit, reorder_level, expiry_date (optional)'},
            {'key': 'menu', 'label': 'Menu', 'done': done['menu'],
             'desc': 'Menu items with prices. Enables profitability analytics.',
             'columns': 'item_name, category, price, cost, is_available'},
            {'key': 'orders', 'label': 'Historical Orders', 'done': done['orders'],
             'desc': 'Past order records for demand analysis.',
             'columns': 'order_date, order_id, item_name, quantity, amount, order_type'},
            {'key': 'customers', 'label': 'Customers', 'done': done['customers'],
             'desc': 'Customer list with visit history for segmentation.',
             'columns': 'name, phone, email, visit_count, total_spend'},
        ]
        done_count = sum(1 for t in upload_types if t['done'])
        readiness_score = int((done_count / len(upload_types)) * 100)

        return Response({
            'upload_types': upload_types,
            'datasets': datasets,
            'readiness_score': readiness_score,
            'done_count': done_count,
        })


class UploadFileView(APIView):
    """
    POST multipart 'file' -> validates + returns a preview and an upload_token
    (server-side cache, replaces the old session-based preview step).
    POST {upload_token, confirm: true} -> commits the cached rows to MongoDB.
    Large files (>5000 rows) commit immediately and skip the preview step,
    exactly like the old view.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, upload_type):
        business, _ = require_business(request)
        if upload_type not in VALID_TYPES:
            return Response({'error': 'Invalid upload type.'}, status=status.HTTP_400_BAD_REQUEST)

        if request.data.get('confirm') == '1' or request.data.get('confirm') is True:
            token = request.data.get('upload_token')
            payload = cache.get(f'upload_preview_{token}') if token else None
            if not payload:
                return Response({'error': 'Preview expired. Please re-upload the file.'}, status=status.HTTP_400_BAD_REQUEST)
            commit_upload(payload['records'], upload_type, business.mongo_id, payload['filename'], payload['row_count'])
            cache.delete(f'upload_preview_{token}')
            return Response({'ok': True, 'row_count': payload['row_count']})

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': 'Please select a file to upload.'}, status=status.HTTP_400_BAD_REQUEST)

        result = validate_and_preview(uploaded_file, upload_type)
        if result['status'] == 'error':
            return Response({'error': result['message']}, status=status.HTTP_400_BAD_REQUEST)

        if result['row_count'] <= MAX_PREVIEW_ROWS:
            token = uuid.uuid4().hex
            cache.set(f'upload_preview_{token}', {
                'records': result['records'],
                'filename': uploaded_file.name,
                'row_count': result['row_count'],
            }, timeout=UPLOAD_CACHE_TTL)
            result['upload_token'] = token
            return Response(result)

        commit_upload(result['records'], upload_type, business.mongo_id, uploaded_file.name, result['row_count'])
        return Response({'ok': True, 'row_count': result['row_count'], 'committed_immediately': True})


class DownloadTemplateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, upload_type):
        return generate_template_csv(upload_type)
