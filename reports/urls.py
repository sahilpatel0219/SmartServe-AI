from django.urls import path
from . import views
app_name = 'reports'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('export/<str:report_type>/<str:fmt>/', views.export_view, name='export'),
]
