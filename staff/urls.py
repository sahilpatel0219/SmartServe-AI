from django.urls import path
from . import views
app_name = 'staff'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('add/', views.add_employee_view, name='add_employee'),
    path('<str:employee_id>/edit/', views.edit_employee_view, name='edit_employee'),
    path('<str:employee_id>/delete/', views.delete_employee_view, name='delete_employee'),
    path('attendance/', views.mark_attendance_view, name='attendance'),
]
