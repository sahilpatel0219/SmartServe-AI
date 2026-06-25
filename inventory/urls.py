from django.urls import path
from . import views
app_name = 'inventory'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('add/', views.add_stock_view, name='add_stock'),
]
