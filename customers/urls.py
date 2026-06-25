from django.urls import path
from . import views
app_name = 'customers'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('add/', views.add_customer_view, name='add'),
]
