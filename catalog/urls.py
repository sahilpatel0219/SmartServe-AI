from django.urls import path
from . import views
app_name = 'catalog'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('item/new/', views.create_item_view, name='create_item'),
]
