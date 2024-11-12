from django.contrib import admin
from .models import Department, Employee, Attendance, CustomSchedule

admin.site.register(Department)
admin.site.register(Employee)
admin.site.register(Attendance)
admin.site.register(CustomSchedule)
