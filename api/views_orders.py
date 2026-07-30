from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from mongo import collections as col
from .tenancy import require_business

STATUSES = ['pending', 'preparing', 'ready', 'delivered', 'cancelled']
ORDER_TYPES = ['dine_in', 'takeaway', 'delivery', 'qr', 'phone']


def _serialize(order):
    order['id'] = str(order.pop('_id'))
    order['short_id'] = order['id'][-6:].upper()
    return order


def _deduct_inventory(business_id, line_items):
    for line in line_items:
        for ing in line.get('recipe', []):
            name = ing.get('ingredient', '')
            qty_to_deduct = ing.get('quantity', 0) * line['quantity']
            if name and qty_to_deduct > 0:
                col.inventory().update_one(
                    {'business_id': business_id, 'item_name': name},
                    {'$inc': {'quantity': -qty_to_deduct}},
                )


class OrderListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business, _ = require_business(request)
        bid = business.mongo_id
        query = {'business_id': bid}
        status_filter = request.query_params.get('status')
        if status_filter:
            query['status'] = status_filter
        orders = list(col.orders().find(query, sort=[('created_at', -1)], limit=100))
        counts = {s: col.orders().count_documents({'business_id': bid, 'status': s}) for s in STATUSES}
        return Response({
            'orders': [_serialize(o) for o in orders],
            'statuses': STATUSES,
            'counts': counts,
        })

    def post(self, request):
        business, _ = require_business(request)
        bid = business.mongo_id
        data = request.data
        order_type = data.get('order_type', 'dine_in')
        items_in = data.get('items') or []  # [{item_id, quantity}]
        line_items, total = [], 0.0
        for entry in items_in:
            try:
                qty = int(entry.get('quantity') or 0)
            except (TypeError, ValueError):
                qty = 0
            if qty <= 0:
                continue
            try:
                oid = ObjectId(entry.get('item_id'))
            except (InvalidId, TypeError):
                continue
            menu_item = col.menu_items().find_one({'_id': oid, 'business_id': bid})
            if menu_item:
                subtotal = menu_item.get('price', 0) * qty
                total += subtotal
                line_items.append({
                    'item_id': str(oid), 'name': menu_item.get('name', ''),
                    'price': menu_item.get('price', 0), 'quantity': qty,
                    'subtotal': subtotal, 'recipe': menu_item.get('recipe', []),
                })
        if not line_items:
            return Response({'error': 'Add at least one item to the order.'}, status=status.HTTP_400_BAD_REQUEST)

        order = {
            'business_id': bid,
            'order_type': order_type,
            'table_no': str(data.get('table_no', '')).strip(),
            'customer_name': str(data.get('customer_name', '')).strip(),
            'notes': str(data.get('notes', '')).strip(),
            'items': line_items,
            'total_amount': round(total, 2),
            'status': 'pending',
            'created_at': datetime.now(timezone.utc),
        }
        result = col.orders().insert_one(order)
        _deduct_inventory(bid, line_items)
        order['_id'] = result.inserted_id
        return Response(_serialize(order), status=status.HTTP_201_CREATED)


class OrderStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, order_id):
        business, _ = require_business(request)
        new_status = request.data.get('status', '')
        if new_status not in STATUSES:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            oid = ObjectId(order_id)
        except InvalidId:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        col.orders().update_one(
            {'_id': oid, 'business_id': business.mongo_id},
            {'$set': {'status': new_status, 'updated_at': datetime.now(timezone.utc)}},
        )
        return Response({'status': new_status})


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        business, _ = require_business(request)
        try:
            oid = ObjectId(order_id)
        except InvalidId:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
        order = col.orders().find_one({'_id': oid, 'business_id': business.mongo_id})
        if not order:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize(order))
