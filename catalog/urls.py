from django.urls import path
from . import views
app_name = 'catalog'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('item/new/', views.create_item_view, name='create_item'),
    path('item/<str:item_id>/edit/', views.edit_item_view, name='edit_item'),
    path('item/<str:item_id>/delete/', views.delete_item_view, name='delete_item'),
]
