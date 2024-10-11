from django.urls import path

from . import views

urlpatterns = [
    path('', views.checkin, name='checkin_page'),
    path('checkout/', views.checkout, name='checkout_page'),
    
    path('admin_dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('login/', views.login_view, name='login'),  
    path('departments/', views.departments, name='departments'),
    path('add_employee/', views.add_employee, name='add_employee'),
    path('reports/', views.reports, name='reports'),
    path('attendance/', views.attendance_record, name='attendance_record'),
    path('employeelist/', views.employeelist, name='employeelist'),
    
    path('department/<int:department_id>/', views.viewdepartment, name='viewdepartments'),
    path('logout/', views.logout_view, name='logout'),
    
    
]
