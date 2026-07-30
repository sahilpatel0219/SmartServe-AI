from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from mongo import collections as col
from .tenancy import require_business


def _serialize(doc):
    doc['id'] = str(doc.pop('_id'))
    return doc


class SupplierListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business, _ = require_business(request)
        sups = list(col.suppliers().find({'business_id': business.mongo_id}, sort=[('name', 1)]))
        return Response({'suppliers': [_serialize(s) for s in sups]})

    def post(self, request):
        business, _ = require_business(request)
        data = request.data
        name = str(data.get('name', '')).strip()
        if not name:
            return Response({'error': 'Supplier name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        doc = {
            'business_id': business.mongo_id,
            'name': name,
            'contact_person': str(data.get('contact_person', '')).strip(),
            'phone': str(data.get('phone', '')).strip(),
            'email': str(data.get('email', '')).strip(),
            'address': str(data.get('address', '')).strip(),
            'products': str(data.get('products', '')).strip(),
            'payment_terms': str(data.get('payment_terms', '')).strip(),
            'created_at': datetime.now(timezone.utc),
        }
        result = col.suppliers().insert_one(doc)
        doc['_id'] = result.inserted_id
        return Response(_serialize(doc), status=status.HTTP_201_CREATED)


class SupplierDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, business, supplier_id):
        try:
            oid = ObjectId(supplier_id)
        except InvalidId:
            return None
        return col.suppliers().find_one({'_id': oid, 'business_id': business.mongo_id})

    def patch(self, request, supplier_id):
        business, _ = require_business(request)
        supplier = self._get(business, supplier_id)
        if not supplier:
            return Response({'error': 'Supplier not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = request.data
        name = str(data.get('name', supplier.get('name', ''))).strip()
        if not name:
            return Response({'error': 'Supplier name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        updates = {'name': name, 'updated_at': datetime.now(timezone.utc)}
        for field in ['contact_person', 'phone', 'email', 'address', 'products', 'payment_terms']:
            if field in data:
                updates[field] = str(data[field]).strip()
        col.suppliers().update_one({'_id': supplier['_id'], 'business_id': business.mongo_id}, {'$set': updates})
        supplier.update(updates)
        return Response(_serialize(supplier))

    def delete(self, request, supplier_id):
        business, _ = require_business(request)
        try:
            oid = ObjectId(supplier_id)
        except InvalidId:
            return Response({'error': 'Supplier not found.'}, status=status.HTTP_404_NOT_FOUND)
        col.suppliers().delete_one({'_id': oid, 'business_id': business.mongo_id})
        return Response(status=status.HTTP_204_NO_CONTENT)


class PurchaseOrderListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business, _ = require_business(request)
        bid = business.mongo_id
        sups = [_serialize(s) for s in col.suppliers().find({'business_id': bid}, {'name': 1})]
        pos = [_serialize(p) for p in col.purchase_orders().find({'business_id': bid}, sort=[('created_at', -1)], limit=50)]
        return Response({'suppliers': sups, 'purchase_orders': pos})

    def post(self, request):
        business, _ = require_business(request)
        data = request.data
        doc = {
            'business_id': business.mongo_id,
            'supplier_id': str(data.get('supplier_id', '')),
            'supplier_name': str(data.get('supplier_name', '')),
            'items': str(data.get('items', '')).strip(),
            'total_amount': float(data.get('total_amount') or data.get('total') or 0),
            'status': 'pending',
            'created_at': datetime.now(timezone.utc),
        }
        result = col.purchase_orders().insert_one(doc)
        doc['_id'] = result.inserted_id
        return Response(_serialize(doc), status=status.HTTP_201_CREATED)
