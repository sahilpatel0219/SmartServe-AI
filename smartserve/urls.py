"""
Root URL config.

This backend is API-only: it serves JSON under /api/ and nothing else renders UI.
The React SPA in frontend/ owns every screen. The old Django template routes
(core, accounts, catalog, inventory, …) have been retired — their views and
services are still imported by the api app, so all business logic, ML, and
validation code is preserved; only the HTML-rendering URLs are gone.
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


def api_root(request):
    """Tiny liveness/discovery endpoint so hitting the host root isn't a 404."""
    return JsonResponse({
        'service': 'SmartServe AI API',
        'api_root': '/api/',
        'docs': 'See API.md in the repository root.',
        'frontend': 'React SPA — run `npm run dev --prefix frontend`.',
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('', api_root),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
