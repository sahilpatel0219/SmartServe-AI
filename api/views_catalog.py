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


def _build_recipe(data):
    recipe = data.get('recipe') or []
    return [
        {'ingredient': str(r.get('ingredient', '')).strip(), 'quantity': float(r.get('quantity') or 0), 'unit': str(r.get('unit', '')).strip()}
        for r in recipe if str(r.get('ingredient', '')).strip()
    ]


class MenuItemListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business, _ = require_business(request)
        bid = business.mongo_id
        query = {'business_id': bid}
        category = request.query_params.get('category')
        if category:
            query['category'] = category
        items = list(col.menu_items().find(query, sort=[('category', 1), ('name', 1)]))
        categories = sorted(col.menu_items().distinct('category', {'business_id': bid}))
        return Response({'items': [_serialize(i) for i in items], 'categories': categories})

    def post(self, request):
        business, _ = require_business(request)
        data = request.data
        name = str(data.get('name', '')).strip()
        if not name:
            return Response({'error': 'Item name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        doc = {
            'business_id': business.mongo_id,
            'name': name,
            'category': str(data.get('category', '')).strip(),
            'price': float(data.get('price') or 0),
            'cost': float(data.get('cost') or 0),
            'description': str(data.get('description', '')).strip(),
            'is_available': bool(data.get('is_available', True)),
            'recipe': _build_recipe(data),
            'created_at': datetime.now(timezone.utc),
        }
        result = col.menu_items().insert_one(doc)
        doc['_id'] = result.inserted_id
        return Response(_serialize(doc), status=status.HTTP_201_CREATED)


class MenuItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_item(self, business, item_id):
        try:
            oid = ObjectId(item_id)
        except InvalidId:
            return None
        return col.menu_items().find_one({'_id': oid, 'business_id': business.mongo_id})

    def get(self, request, item_id):
        business, _ = require_business(request)
        item = self._get_item(business, item_id)
        if not item:
            return Response({'error': 'Item not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize(item))

    def patch(self, request, item_id):
        business, _ = require_business(request)
        item = self._get_item(business, item_id)
        if not item:
            return Response({'error': 'Item not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = request.data
        updates = {'updated_at': datetime.now(timezone.utc)}
        for field in ['name', 'category', 'description']:
            if field in data:
                updates[field] = str(data[field]).strip()
        for field in ['price', 'cost']:
            if field in data:
                updates[field] = float(data[field] or 0)
        if 'is_available' in data:
            updates['is_available'] = bool(data['is_available'])
        if 'recipe' in data:
            updates['recipe'] = _build_recipe(data)
        col.menu_items().update_one({'_id': item['_id'], 'business_id': business.mongo_id}, {'$set': updates})
        item.update(updates)
        return Response(_serialize(item))

    def delete(self, request, item_id):
        business, _ = require_business(request)
        try:
            oid = ObjectId(item_id)
        except InvalidId:
            return Response({'error': 'Item not found.'}, status=status.HTTP_404_NOT_FOUND)
        col.menu_items().delete_one({'_id': oid, 'business_id': business.mongo_id})
        return Response(status=status.HTTP_204_NO_CONTENT)
