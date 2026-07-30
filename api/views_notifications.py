from bson import ObjectId
from bson.errors import InvalidId
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from mongo import collections as col
from notifications.views import generate_notifications
from .tenancy import require_business


class NotificationListView(APIView):
    """GET regenerates fresh alerts (same side-effecting behaviour as the old
    index_view) then lists the latest 50."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business, _ = require_business(request)
        bid = business.mongo_id
        generate_notifications(bid)
        notifs = list(col.notifications().find({'business_id': bid}, sort=[('created_at', -1)], limit=50))
        for n in notifs:
            n['id'] = str(n.pop('_id'))
        unread = sum(1 for n in notifs if not n.get('read'))
        return Response({'notifications': notifs, 'unread': unread})


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notif_id):
        business, _ = require_business(request)
        try:
            oid = ObjectId(notif_id)
        except InvalidId:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        col.notifications().update_one(
            {'_id': oid, 'business_id': business.mongo_id}, {'$set': {'read': True}}
        )
        return Response({'ok': True})


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        business, _ = require_business(request)
        col.notifications().update_many(
            {'business_id': business.mongo_id, 'read': False}, {'$set': {'read': True}}
        )
        return Response({'ok': True})
