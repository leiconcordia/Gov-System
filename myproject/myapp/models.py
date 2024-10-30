from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Employee(models.Model):
    employee_id = models.CharField(max_length=100, unique=True)
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    username = models.CharField(max_length=100, unique=True, default='defaultuser')

    password = models.CharField(max_length=128, default='defaultpassword')

    department_name = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='employees')
    
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.employee_id})"

    class Meta:
        ordering = ['-updated', '-created']


class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    time_in = models.TimeField()
    time_out = models.TimeField(null=True, blank=True)
    
    # Status options for arrival and departure
    arrival_status = models.CharField(max_length=10, choices=[
        ('ontime', 'On Time'),
        ('late', 'Late'),
        ('absent', 'Absent'),
    ])
    timeout_status = models.CharField(max_length=10, choices=[  # New status for time_out
        ('ontime', 'On Time'),
        ('early', 'Left Early'),     # "Undertime"
        ('overtime', 'Overtime'),    # "Overtime"
    ], null=True, blank=True)

    class Meta:
        unique_together = ('employee', 'date')  # Ensure one record per employee per day

    def __str__(self):
        return f"{self.employee} - {self.date} - Arrival: {self.arrival_status}, Departure: {self.timeout_status}"
