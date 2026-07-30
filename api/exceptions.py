"""
Custom DRF exception handler.

DRF's default handler only converts recognised exceptions (APIException,
Http404, PermissionDenied) into a JSON Response; anything else propagates to
Django, which — with DEBUG=True — renders a full HTML stack-trace page. That
page was leaking into the React app as a wall of raw text (e.g. a transient
MongoDB ServerSelectionTimeoutError/AutoReconnect on the assistant chat
endpoint), which is both ugly and exposes internals to the client.

This wraps the default handler and, for anything it doesn't already handle,
returns a clean {"error": "..."} JSON body instead of letting it fall through
to Django's HTML error page.
"""
import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework import status

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    # Anything DRF doesn't recognise (pymongo errors, unexpected bugs, etc.)
    # gets logged with a full traceback server-side, but the client only sees
    # a short, safe message — never a stack trace.
    logger.exception('Unhandled exception in %s', context.get('view'))
    return Response(
        {'error': f'{exc.__class__.__name__}: {exc}'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
