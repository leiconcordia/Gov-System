from django.urls import path

from . import views
from .views import viewdepartment
from .views import employee_dashboard

urlpatterns = [
    path('', views.checkin, name='checkin_page'),
    
    
    path('signin/', views.signin, name='signin'),
    path('employee-dashboard/', views.employee_dashboard, name='employee-dashboard'),
    
    path('attendance_records/', views.attendance_records, name='attendance'),
    
    path('admin_dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    
    
    path('login/', views.login_view, name='login'),  
    path('departments/', views.departments, name='departments'),
    path('settings/', views.settings, name='settings'),
    

    path('change-password/', views.change_password, name='change_password'),
    
  
    
    path('employeelist/', views.employeelist, name='employeelist'),
    
    path('departments/view/<int:department_id>/', viewdepartment, name='viewdepartment'),
    
    path('logout/', views.logout_view, name='logout'),
    
    path('employee/<str:employee_id>/', views.view_employee, name='view_employee'),
    
    path('employee/edit/<int:employee_id>/', views.edit_employee, name='edit_employee'),
    path('employee/archive/<int:employee_id>/', views.archive_employee, name='archive_employee'),
    
     
    path('add-department/', views.add_department, name='add_department'),


     path('schedules/', views.schedule_list, name='schedule_list'),

    path('archived-employees/', views.archived_employees, name='archived_employees'),
    path('unarchive/<int:employee_id>/', views.unarchive_employee, name='unarchive_employee'),


    path('edit_sched/<int:schedule_id>/', views.edit_schedule, name='edit_sched'),
    path('delete_sched/<int:schedule_id>/', views.delete_schedule, name='delete_sched'),
     path('employee/delete/<int:employee_id>/', views.delete_employee, name='delete_employee'),

    
    path('get-badge-count/', views.get_badge_count, name='get_badge_count'),
    path('reset-badge-count/', views.reset_badge_count_view, name='reset_badge_count'),
    
    
]
