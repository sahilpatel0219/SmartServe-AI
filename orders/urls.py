from django.urls import path
from . import views
app_name = 'orders'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('new/', views.create_order_view, name='create'),
    path('<str:order_id>/', views.detail_view, name='detail'),
    path('<str:order_id>/status/', views.update_status_view, name='update_status'),
]
