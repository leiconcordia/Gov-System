from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Employee(models.Model):
    
    employee_id = models.CharField(max_length=100, unique=True)  # Set a sensible default
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    department_name = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='employees')
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.employee_id})"


class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=10, choices=[
        ('ontime', 'On Time'),
        ('late', 'Late'),
        ('absent', 'Absent'),
    ])

    class Meta:
        unique_together = ('employee', 'date')  # Ensure one record per employee per day

    def __str__(self):
        return f"{self.employee} - {self.date} - {self.status}"