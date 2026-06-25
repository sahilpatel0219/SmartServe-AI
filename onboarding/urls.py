from django.urls import path
from . import views

app_name = 'onboarding'

urlpatterns = [
    path('business/new/', views.create_business_view, name='create_business'),
    path('data/', views.upload_center_view, name='upload_center'),
    path('data/upload/<str:upload_type>/', views.upload_file_view, name='upload_file'),
    path('data/template/<str:upload_type>/', views.download_template_view, name='download_template'),
]
