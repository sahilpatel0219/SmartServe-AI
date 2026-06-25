from django.urls import path
from . import views
app_name = 'assistant'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('chat/', views.chat_view, name='chat'),
]
