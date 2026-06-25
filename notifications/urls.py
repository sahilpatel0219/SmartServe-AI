from django.urls import path
from . import views
app_name = 'notifications'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('<str:notif_id>/read/', views.mark_read_view, name='mark_read'),
    path('mark-all-read/', views.mark_all_read_view, name='mark_all_read'),
]
