from django.urls import path
from . import views
app_name = 'orders'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('new/', views.create_order_view, name='create'),
]
