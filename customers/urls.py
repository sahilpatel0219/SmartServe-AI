from django.urls import path
from . import views
app_name = 'customers'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('add/', views.add_customer_view, name='add'),
    path('<str:customer_id>/edit/', views.edit_customer_view, name='edit'),
    path('<str:customer_id>/', views.detail_view, name='detail'),
]
