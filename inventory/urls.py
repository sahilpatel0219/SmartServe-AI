from django.urls import path
from . import views
app_name = 'inventory'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('add/', views.add_stock_view, name='add_stock'),
    path('<str:item_id>/edit/', views.edit_stock_view, name='edit_stock'),
    path('<str:item_id>/delete/', views.delete_stock_view, name='delete_stock'),
]
