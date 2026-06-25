from django.urls import path
from . import views
app_name = 'staff'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('add/', views.add_employee_view, name='add_employee'),
    path('attendance/', views.mark_attendance_view, name='attendance'),
]
