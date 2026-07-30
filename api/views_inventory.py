from datetime import datetime, timezone, date

from bson import ObjectId
from bson.errors import InvalidId
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from mongo import collections as col
from .tenancy import require_business


def _annotate(item, today):
    item['id'] = str(item.pop('_id'))
    qty = float(str(item.get('quantity', 0)).replace(',', '') or 0)
    reorder = float(str(item.get('reorder_level', 0)).replace(',', '') or 0)
    item['low_stock'] = qty <= reorder
    exp = item.get('expiry_date', '')
    if exp:
        try:
            import pandas as pd
            exp_date = pd.to_datetime(str(exp)).date()
            item['days_to_expiry'] = (exp_date - today).days
            item['expiring_soon'] = item['days_to_expiry'] <= 7
        except Exception:
            item['days_to_expiry'] = None
            item['expiring_soon'] = False
    else:
        item['days_to_expiry'] = None
        item['expiring_soon'] = False
    return item


class InventoryListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business, _ = require_business(request)
        bid = business.mongo_id
        items = list(col.inventory().find({'business_id': bid}, sort=[('item_name', 1)]))
        today = date.today()
        items = [_annotate(i, today) for i in items]
        return Response({
            'items': items,
            'low_stock_count': sum(1 for i in items if i['low_stock']),
            'expiring_count': sum(1 for i in items if i['expiring_soon']),
        })

    def post(self, request):
        """Upsert-by-name, matching the old add_stock_view behaviour."""
        business, _ = require_business(request)
        bid = business.mongo_id
        data = request.data
        item_name = str(data.get('item_name', '')).strip()
        if not item_name:
            return Response({'error': 'Item name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        doc = {
            'business_id': bid,
            'item_name': item_name,
            'quantity': float(data.get('quantity') or 0),
            'unit': str(data.get('unit', '')).strip(),
            'cost_per_unit': float(data.get('cost_per_unit') or 0),
            'reorder_level': float(data.get('reorder_level') or 0),
            'expiry_date': str(data.get('expiry_date', '')).strip() or None,
            'category': str(data.get('category', '')).strip(),
            'supplier': str(data.get('supplier', '')).strip(),
            'created_at': datetime.now(timezone.utc),
        }
        existing = col.inventory().find_one({'business_id': bid, 'item_name': item_name})
        if existing:
            col.inventory().update_one({'_id': existing['_id']}, {'$set': doc})
            doc['_id'] = existing['_id']
        else:
            result = col.inventory().insert_one(doc)
            doc['_id'] = result.inserted_id
        return Response(_annotate(doc, date.today()), status=status.HTTP_201_CREATED)


class InventoryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_item(self, business, item_id):
        try:
            oid = ObjectId(item_id)
        except InvalidId:
            return None
        return col.inventory().find_one({'_id': oid, 'business_id': business.mongo_id})

    def get(self, request, item_id):
        business, _ = require_business(request)
        item = self._get_item(business, item_id)
        if not item:
            return Response({'error': 'Item not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_annotate(item, date.today()))

    def patch(self, request, item_id):
        business, _ = require_business(request)
        item = self._get_item(business, item_id)
        if not item:
            return Response({'error': 'Item not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = request.data
        updates = {'updated_at': datetime.now(timezone.utc)}
        for field in ['item_name', 'unit', 'category']:
            if field in data:
                updates[field] = str(data[field]).strip()
        for field in ['quantity', 'cost_per_unit', 'reorder_level']:
            if field in data:
                updates[field] = float(data[field] or 0)
        if 'expiry_date' in data:
            updates['expiry_date'] = str(data['expiry_date']).strip() or None
        col.inventory().update_one({'_id': item['_id'], 'business_id': business.mongo_id}, {'$set': updates})
        item.update(updates)
        return Response(_annotate(item, date.today()))

    def delete(self, request, item_id):
        business, _ = require_business(request)
        try:
            oid = ObjectId(item_id)
        except InvalidId:
            return Response({'error': 'Item not found.'}, status=status.HTTP_404_NOT_FOUND)
        col.inventory().delete_one({'_id': oid, 'business_id': business.mongo_id})
        return Response(status=status.HTTP_204_NO_CONTENT)
