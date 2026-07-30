from datetime import datetime, timezone

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from mongo import collections as col
from assistant.views import _starter_chips
from .tenancy import require_business


class AssistantStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business, _ = require_business(request)
        bid = business.mongo_id
        has_data = col.sales_records().count_documents({'business_id': bid}) > 0
        return Response({
            'has_data': has_data,
            'starter_chips': _starter_chips(bid),
            'llm_enabled': bool(getattr(settings, 'LLM_PROVIDER', '') and getattr(settings, 'LLM_API_KEY', '')),
        })


class AssistantChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        business, membership = require_business(request)
        role = getattr(membership, 'role', 'staff') or 'staff'
        question = str(request.data.get('message', '')).strip()
        if not question:
            return Response({'error': 'Empty message'}, status=status.HTTP_400_BAD_REQUEST)

        from assistant.engine import respond
        result = respond(question, business.mongo_id, role, business.name, user_id=request.user.id)
        return Response({
            'reply': result.get('reply', ''),
            'chips': result.get('chips', []),
            'intent': result.get('intent'),
            'needs_clarification': result.get('needs_clarification', False),
        })


class AssistantFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        business, _ = require_business(request)
        rating = request.data.get('rating')
        if rating not in ('up', 'down'):
            return Response({'error': 'Invalid rating'}, status=status.HTTP_400_BAD_REQUEST)

        question = str(request.data.get('question', ''))[:1000]
        answer = str(request.data.get('answer', ''))[:2000]
        try:
            col.get_db()['assistant_feedback'].insert_one({
                'business_id': business.mongo_id, 'user_id': request.user.id,
                'question': question, 'answer': answer, 'rating': rating,
                'created_at': datetime.now(timezone.utc),
            })
        except Exception:
            pass
        if rating == 'down':
            from assistant.guards import log_gap
            log_gap(business.mongo_id, request.user.id, question, 'thumbs_down', 'user_flagged_unhelpful')
        return Response({'ok': True})
