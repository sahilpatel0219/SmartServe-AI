from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from mongo import collections as col
from .tenancy import require_business


def _segment(visits, total_spend):
    if total_spend >= 5000 or visits >= 20:
        return 'VIP'
    elif visits >= 5:
        return 'Regular'
    return 'Inactive'


def _serialize(c):
    c['id'] = str(c.pop('_id'))
    c['segment'] = _segment(c.get('visit_count', 0), c.get('total_spend', 0))
    return c


class CustomerListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business, _ = require_business(request)
        bid = business.mongo_id
        custs = [_serialize(c) for c in col.customers().find({'business_id': bid}, sort=[('name', 1)])]
        segment_filter = request.query_params.get('segment')
        if segment_filter:
            custs = [c for c in custs if c['segment'] == segment_filter]
        return Response({'customers': custs, 'segments': ['VIP', 'Regular', 'Inactive']})

    def post(self, request):
        business, _ = require_business(request)
        name = str(request.data.get('name', '')).strip()
        if not name:
            return Response({'error': 'Customer name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        doc = {
            'business_id': business.mongo_id,
            'name': name,
            'phone': str(request.data.get('phone', '')).strip(),
            'email': str(request.data.get('email', '')).strip(),
            'visit_count': 0,
            'total_spend': 0.0,
            'notes': str(request.data.get('notes', '')).strip(),
            'created_at': datetime.now(timezone.utc),
        }
        result = col.customers().insert_one(doc)
        doc['_id'] = result.inserted_id
        return Response(_serialize(doc), status=status.HTTP_201_CREATED)


class CustomerDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, business, customer_id):
        try:
            oid = ObjectId(customer_id)
        except InvalidId:
            return None
        return col.customers().find_one({'_id': oid, 'business_id': business.mongo_id})

    def get(self, request, customer_id):
        business, _ = require_business(request)
        customer = self._get(business, customer_id)
        if not customer:
            return Response({'error': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)
        cust_id = customer['_id']
        name = customer.get('name', '')
        data = _serialize(customer)
        orders = list(col.orders().find(
            {'business_id': business.mongo_id, 'customer_name': name},
            sort=[('created_at', -1)], limit=10,
        ))
        for o in orders:
            o['_id'] = str(o['_id'])
        data['recent_orders'] = orders
        return Response(data)

    def patch(self, request, customer_id):
        """Only profile fields are editable; visit_count/total_spend are system-managed."""
        business, _ = require_business(request)
        customer = self._get(business, customer_id)
        if not customer:
            return Response({'error': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)
        name = str(request.data.get('name', customer.get('name', ''))).strip()
        if not name:
            return Response({'error': 'Customer name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        updates = {
            'name': name,
            'phone': str(request.data.get('phone', customer.get('phone', ''))).strip(),
            'email': str(request.data.get('email', customer.get('email', ''))).strip(),
            'notes': str(request.data.get('notes', customer.get('notes', ''))).strip(),
            'updated_at': datetime.now(timezone.utc),
        }
        col.customers().update_one({'_id': customer['_id'], 'business_id': business.mongo_id}, {'$set': updates})
        customer.update(updates)
        return Response(_serialize(customer))
