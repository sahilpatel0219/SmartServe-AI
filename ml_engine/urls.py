from django.urls import path
from . import views
app_name = 'ml_engine'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('analyze/', views.analyze_view, name='analyze'),
    path('insights/', views.insights_view, name='insights'),
    path('run/', views.run_analysis_view, name='run_analysis'),
]
