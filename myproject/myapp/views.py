from django.http import HttpResponse
from django.shortcuts import render, redirect    
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from .models import Department,Employee, Attendance
from django.utils import timezone
import pytz
    


# User = get_user_model()
# user = User.objects.get(username='admin')  # Replace with your username
# print(user.password)  # This will show a hash, confirming the user exists.


def checkin(request):
    if request.method == 'POST':
        employee_input = request.POST.get('employee_input')  # This can be either ID or name

        # Try to find the employee by ID or by name (last_name, first_name)
        try:
            employee = Employee.objects.get(employee_id=employee_input)
        except Employee.DoesNotExist:
            try:
                first_name, last_name = employee_input.split()  # Expecting "Last First"
                employee = Employee.objects.get(first_name__iexact=first_name, last_name__iexact=last_name)
            except (Employee.DoesNotExist, ValueError):
                return HttpResponse("Employee not found.", status=404)

        now_utc = timezone.now()

        # Convert to Philippine time
        philippine_tz = pytz.timezone('Asia/Manila')
        now_philippine = now_utc.astimezone(philippine_tz)

        current_time = now_philippine.time()
        current_date = now_philippine.date()

        # Check if the attendance has already been marked for today
        if Attendance.objects.filter(employee=employee, date=current_date).exists():
            return HttpResponse("Attendance already marked for today.", status=400)

        # Determine attendance status
        if current_time < timezone.datetime.strptime('07:30', '%H:%M').time():
            status = 'ontime'
        elif current_time < timezone.datetime.strptime('12:00', '%H:%M').time():
            status = 'late'
        else:
            status = 'absent'

        # Create a new attendance record
        Attendance.objects.create(
            employee=employee,
            date=current_date,
            time=current_time,
            status=status
        )

        # Render the same template with a success alert
        return render(request, 'checkin.html', {'alert_message': 'Attendance marked successfully!'})

    # Handle GET request
    return render(request, 'checkin.html')

@login_required
def admin_dashboard_view(request):
    return render(request, 'admin_dashboard.html')

def logout_view(request):
    logout(request)
    return redirect('login')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        print(f"Attempting login with Username: {username}")  # Log only the username for security
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            print(f"User {username} logged in successfully.")  # Success message
            return redirect('admin_dashboard')
        else:
            print("Login failed")  # Debugging
            return HttpResponse("Invalid login credentials. Please try again.")
    
    if request.user.is_authenticated:
        return redirect('admin_dashboard')

    return render(request, 'login.html')

@login_required
def departments(request):
    departments = Department.objects.all()
    context = {
        "departments": departments  # Use a plural name for clarity
    }
    return render(request, 'departments.html', context)

@login_required
def reports(request):
    return render(request, 'reports.html')


@login_required
def add_employee(request):
    if request.method == 'POST':
        # Extract data from the form
        employee_id = request.POST['employeeId']
        first_name = request.POST['firstName']
        last_name = request.POST['lastName']
        department_id = request.POST['department_name']  # Assuming department is passed as ID

        # Create a new Employee instance
        employee = Employee(
            employee_id=employee_id,
            first_name=first_name,
            last_name=last_name,
            department_name_id=department_id  # Use the department ID here
        )
        
        # Save the employee to the database
        employee.save()

        # Redirect to the employee list page or a success page
        return redirect('employeelist')  # Adjust this to your actual success page

    # If GET request, fetch all departments to display in the form
    departments = Department.objects.all()

    context = {
        "departments": departments  # Use a plural name for clarity
    }
    
    return render(request, 'add_employee.html', context)

@login_required
def attendance_record(request):
    return render(request, 'attendance_record.html')

@login_required
def employeelist(request):
    employee = Employee.objects.all()
    context = {
        "employee": employee
 }
    return render(request, 'employeelist.html', context)



def viewdepartment(request, department_id):
    
    department = Department.objects.get(id=department_id)
    employees = Attendance.objects.all()
    
    attendance_data = {}
    
    # for employee in employees:    
    #     attendance_record = Attendance.objects.filter(employee=employee).order_by('-date').first()
    #     if attendance_record:
    #         attendance_data[employee.id] = {
    #             'status': attendance_record.status,
    #             'time': attendance_record.time,
    #         }
    #     else:
    #         attendance_data[employee.id] = {
    #             'status': 'not yet marked',  # No attendance record
    #             'time': 'not yet marked',    # No attendance time
    #         }

    # Render the template with the department, employees, and attendance data
    return render(request, 'viewdepartments.html', {
        'department': department,
        'employees': employees,
        'attendance_data': attendance_data,
    })
    





