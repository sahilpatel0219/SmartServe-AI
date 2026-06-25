from django.urls import path
from . import views
app_name = 'suppliers'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('add/', views.add_supplier_view, name='add'),
    path('purchase-orders/', views.purchase_order_view, name='purchase_orders'),
]
