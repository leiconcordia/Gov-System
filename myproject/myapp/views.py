from django.http import HttpResponse
from django.shortcuts import render, redirect    
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from .models import Department,Employee, Attendance, CustomSchedule
from django.utils import timezone
import pytz
from django.db.models import Count, Q, F
from django.contrib.auth.hashers import make_password
from django.http import HttpResponseNotFound
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from datetime import date
from datetime import timedelta
from datetime import datetime



def get_schedule(current_date):
    # Default time-in and time-out
    default_time_in = timezone.datetime.strptime('08:10', '%H:%M').time()
    default_time_out = timezone.datetime.strptime('18:10', '%H:%M').time()

    try:
        # Fetch custom schedule if available
        custom_schedule = CustomSchedule.objects.get(date=current_date)
        time_in = custom_schedule.time_in
        time_out = custom_schedule.time_out
        print(f"Custom schedule found: Time In: {time_in}, Time Out: {time_out}")
    except CustomSchedule.DoesNotExist:
        # Use default schedule if custom not found
        time_in = default_time_in
        time_out = default_time_out
        print(f"No custom schedule found. Using default times: Time In: {time_in}, Time Out: {time_out}")
    
    return time_in, time_out



def checkin(request):
    # Current time in Philippine timezone
    now_utc = timezone.now()
    philippine_tz = pytz.timezone('Asia/Manila')
    now_philippine = now_utc.astimezone(philippine_tz)
    current_date = now_philippine.date()
    current_time = now_philippine.time()

    # Get the schedule
    time_in, time_out = get_schedule(current_date)
    current_time_dt = timezone.datetime.combine(current_date, current_time)
    time_in_dt = timezone.datetime.combine(current_date, time_in)
    time_out_dt = timezone.datetime.combine(current_date, time_out)

    # Calculate half-gap time
    gap_time = time_out_dt - time_in_dt
    half_gap_time = time_in_dt + gap_time / 2  # Halfway point in datetime
    print(f"Time-in: {time_in}, Time-out: {time_out}, Half Gap Time: {half_gap_time.time()}")

    if request.method == 'POST':
        employee_input = request.POST.get('employee_input')
        print(f"Employee Input: {employee_input}")

        try:
            # Try to find employee by ID or by name
            employee = Employee.objects.get(employee_id=employee_input)
        except Employee.DoesNotExist:
            try:
                first_name, last_name = employee_input.split()
                employee = Employee.objects.get(first_name__iexact=first_name, last_name__iexact=last_name)
            except (Employee.DoesNotExist, ValueError):
                return render(request, 'checkin.html', {
        'employee_not_found': 'please try again.'
                })
            
        

        # Get or create attendance record
        attendance, _ = Attendance.objects.get_or_create(employee=employee, date=current_date)

        # Check-in logic
        if attendance.time_in is None:  # First-time check-in
            if current_time_dt <= time_in_dt:
                attendance.arrival_status = 'ontime'
            elif current_time_dt < half_gap_time:
                attendance.arrival_status = 'late'
            else:
                # If time-in period has passed and no check-in is recorded
                attendance.arrival_status = 'absent'
                attendance.save()
                return HttpResponse("Time-in period has passed. You are marked absent.", status=400)
            


            # Save time-in and prevent re-checkin
            attendance.time_in = current_time
            attendance.save()
            return render(request, 'checkin.html', {
    'alert_message': 'Attendance marked successfully!',
    'employee_name': f"{employee.first_name} {employee.last_name}"
})


        # Prevent re-checkin if already checked in and before half_gap_time
        if attendance.time_in is not None and current_time_dt < half_gap_time:
             return render(request, 'checkin.html', {
        'already_checked_in_message': 'You have already checked in for today.',
        'employee_name': f"{employee.first_name} {employee.last_name}"
    })

        # Time-out logic
        if attendance.time_out is None and current_time_dt >= half_gap_time:
            overtime_window = time_out_dt + timedelta(hours=3)

            if time_out_dt <= current_time_dt < overtime_window:
                attendance.timeout_status = 'on time'
            elif current_time_dt >= overtime_window:
                attendance.timeout_status = 'overtime'
            elif half_gap_time <= current_time_dt < time_out_dt:
                attendance.timeout_status = 'left early'
            else:
                attendance.timeout_status = 'on time'

            # Save time-out
            attendance.time_out = current_time_dt
            attendance.save()
            return render(request, 'checkin.html', {
        'timeout_alert_message': 'Time-out marked successfully!',
        'employee_name': f"{employee.first_name} {employee.last_name}"
    })
    # Render the checkin page if no form has been submitted
    return render(request, 'checkin.html')




def signin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            # Fetch the employee by username
            employee = Employee.objects.get(username=username)

            # Compare the provided password with the hashed password
            if check_password(password, employee.password):  # Secure comparison
                # Log the employee in by storing their ID in the session
                request.session['employee_id'] = employee.employee_id
                return redirect('employee-dashboard')  # Redirect to the employee dashboard
            else:
                messages.warning(request, "Invalid username or password.")
        except Employee.DoesNotExist:
            messages.warning(request, "Invalid username or password.")

    return render(request, 'signin.html')






def employee_dashboard(request):
    print("Employee dashboard view accessed") 
    employee_id = request.session.get('employee_id')
    
    if not employee_id:
        return redirect('signin')
    # Assuming employee_id is being passed as a string
   
      # Fetch employee using get_object_or_404
    employee = Employee.objects.get( employee_id=employee_id)

     # Get the current month in 'YYYY-MM' format as the default
    current_month = datetime.now().strftime('%Y-%m')

    # Get the selected month from the request, use current_month as default
    selected_month = request.GET.get('month', current_month)
    
    # Filter attendance records if a month is selected
    if selected_month:
        try:
            year, month = map(int, selected_month.split('-'))  # Unpack year and month
            attendance_records = Attendance.objects.filter(
                employee=employee,
                date__year=year,
                date__month=month
            )
        except ValueError:
            # Handle the error if the format is incorrect
            attendance_records = Attendance.objects.filter(employee=employee)
    return render(request, 'employee_dashboard.html', {
        'employee': employee,
        'attendance_records': attendance_records,
        'selected_month': selected_month,
    })



@login_required
def employeelist(request):
    # Handle the signup process
    if request.method == 'POST':
        
        # Extract data from the form
        employee_id = request.POST['employeeId']
        first_name = request.POST['firstName']
        last_name = request.POST['lastName']
        username = request.POST['username']
        password = request.POST['password']
        department_id = request.POST['department_name']
        

        # Create a new Employee instance with hashed password
        employee = Employee(
            employee_id=employee_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            password=make_password(password),
            department_name_id=department_id
        )
        
        # Save the employee to the database
        employee.save()

        # Optionally, you could return a success message or redirect
        # return redirect('employeelist')

    # Handle search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        employees = Employee.objects.filter(
            Q(employee_id__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(department_name__name__icontains=search_query)
        )
    else:
        employees = Employee.objects.all()

    departments = Department.objects.all()  # Fetch departments here
    
    context = {
        "employees": employees,
        "departments": departments
    }
    return render(request, 'employeelist.html', context)


def edit_employee(request, employee_id):
    # Retrieve the employee to edit
    employee = Employee.objects.get(id=employee_id)
    
    if request.method == 'POST':
        # Get the department ID from the form
        department_id = request.POST.get('department_name')
        
        try:
            # Retrieve the department using the ID from the form
            department = Department.objects.get(id=department_id)
            
            # Update the employee's other fields
            employee.first_name = request.POST.get('firstName')
            employee.last_name = request.POST.get('lastName')
            

            # Only update the password if it's provided
            if request.POST.get('password'):
                employee.password = request.POST.get('password')
            
            # Assign the retrieved department object to the employee
            employee.department_name = department
            
            # Save the updated employee instance
            employee.save()
            
            # Redirect after saving the employee
           

        except Department.DoesNotExist:
            # Handle case when the department ID is invalid
            return render(request, 'employeelist.html', {
                'employee': employee, 
                'departments': Department.objects.all(),
                'error_message': "Department does not exist."
            })
    
    # If it's a GET request, render the form with the employee's existing data
    return render(request, 'employeelist.html', {
    'employees': Employee.objects.all(),  # Pass updated employee list
    'departments': Department.objects.all(),
    'success_message': "Employee updated successfully."
})

    
    
@login_required
def delete_employee(request, employee_id):
    # Ensure the employee exists
    employee = Employee.objects.get(pk=employee_id)  # This is correct

    # Delete the employee
    employee.delete()
    
    # Prepare the alert message
    alert_message = f'Employee "{employee.first_name} {employee.last_name}" deleted successfully!'
    
    # Use Django's messages framework to add the alert message
    messages.success(request, alert_message)

    # Redirect back to the employee list page
    return redirect('employeelist')







def schedule_list(request):
    schedules = CustomSchedule.objects.all()
    
    alert_message = None
    alert_icon = None

    # Handle form submission for creating or updating a schedule
    if request.method == 'POST':
        selected_date = request.POST.get('selected_date')
        custom_timein = request.POST.get('custom_timein')
        custom_timeout = request.POST.get('custom_timeout')
        reason = request.POST.get('reason')

        if selected_date and custom_timein and custom_timeout and reason:
            try:
                time_in = timezone.datetime.strptime(custom_timein, '%H:%M').time()
                time_out = timezone.datetime.strptime(custom_timeout, '%H:%M').time()

                # Create or update the schedule for the specified date
                custom_schedule, created = CustomSchedule.objects.update_or_create(
                    date=selected_date,
                    defaults={'time_in': time_in, 'time_out': time_out, 'reason': reason}
                )
                
                # Dynamically include the selected_date and reason in the alert message
                alert_message = (
                    f'Custom schedule for {reason} set successfully on {selected_date}!'
                    if created
                    else f'Custom schedule for "{reason}" updated successfully on {selected_date}!'
                )
                alert_icon = 'success'
            except ValueError as ve:
                alert_message = f'Error parsing time: {str(ve)}'
                alert_icon = 'error'
            except Exception as e:
                alert_message = f'An unexpected error occurred: {str(e)}'
                alert_icon = 'error'
        else:
            alert_message = 'Please provide all required fields!'
            alert_icon = 'warning'

    # Render the schedule list with any alert messages
    return render(request, 'schedule_list.html', {
        'schedules': schedules,
        'alert_message': alert_message,
        'alert_icon': alert_icon
    })



@login_required
def edit_schedule(request, schedule_id):
    schedule = CustomSchedule.objects.get(id=schedule_id)

    if request.method == 'POST':
        selected_date = request.POST.get('selected_date')
        custom_timein = request.POST.get('custom_timein')
        custom_timeout = request.POST.get('custom_timeout')
        reason = request.POST.get('reason')

        if selected_date and custom_timein and custom_timeout and reason:
            try:
                time_in = timezone.datetime.strptime(custom_timein, '%H:%M').time()
                time_out = timezone.datetime.strptime(custom_timeout, '%H:%M').time()

                # Update the schedule
                schedule.date = selected_date
                schedule.time_in = time_in
                schedule.time_out = time_out
                schedule.reason = reason
                schedule.save()

                return redirect('schedule_list')  # Redirect to the schedule list after editing
            except ValueError as ve:
                # Handle error
                pass
            except Exception as e:
                # Handle unexpected error
                pass

    return render(request, 'schedule_list.html', {'schedule': schedule})
        
        

@login_required
def delete_schedule(request, schedule_id):
    try:
        schedule = CustomSchedule.objects.get(id=schedule_id)
    except CustomSchedule.DoesNotExist:
        # Handle the case where the schedule does not exist
        alert_message = "Schedule not found."
        alert_icon = "error"
        return render(request, 'schedule_list.html', {
            'alert_message': alert_message,
            'alert_icon': alert_icon,
            'schedules': CustomSchedule.objects.all()
        })

    if request.method == 'POST':
        schedule.delete()
        return redirect('schedule_list')  # Redirect to the schedule list after deletion

    return render(request, 'confirm_delete.html', {'schedule': schedule})

@login_required
def admin_dashboard_view(request):
    # Get today's date
    today = timezone.now().astimezone(pytz.timezone('Asia/Manila')).date()
    attendance_records = Attendance.objects.filter(date=today)
    
    # Fetch attendance records for today
    attendance_records = Attendance.objects.filter(date=today)
    
    print(f"Attendance records for today: {attendance_records}")
    
    # Check if the attendance records contain any data
    if not attendance_records.exists():
        print("No attendance records found for today.")
    else:
        print(f"Found {attendance_records.count()} attendance records for today.")

    context = {
        'attendance_records': attendance_records
    }
    
    return render(request, 'admin_dashboard.html', context)

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
            messages.warning(request, "Try again")
            return redirect('login')
    
    if request.user.is_authenticated:
        return redirect('admin_dashboard')

    return render(request, 'login.html')











@login_required
def view_employee(request, employee_id):
    # Assuming employee_id is being passed as a string
    try:
        # Fetch employee by employee_id (which is a CharField)
        employee = Employee.objects.get(employee_id=employee_id)
    except Employee.DoesNotExist:
        return HttpResponseNotFound("Employee not found.")
    # Get the current month in 'YYYY-MM' format as the default
    current_month = datetime.now().strftime('%Y-%m')

    # Get the selected month from the request, use current_month as default
    selected_month = request.GET.get('month', current_month)
    
    attendance_records = Attendance.objects.filter(employee=employee)  # Default to all records
    
    # Filter attendance records if a month is selected
    if selected_month:
        try:
            year, month = map(int, selected_month.split('-'))  # Unpack year and month
            attendance_records = Attendance.objects.filter(
                employee=employee,
                date__year=year,
                date__month=month
            )
        except ValueError:
            # Handle the error if the format is incorrect
            attendance_records = Attendance.objects.filter(employee=employee)
    return render(request, 'view_employee.html', {
        'employee': employee,
        'attendance_records': attendance_records,
        'selected_month': selected_month,
    })







def get_selected_date(request):
    date_str = request.GET.get('date', timezone.now().date().isoformat())
    return timezone.datetime.fromisoformat(date_str).date()


@login_required
def departments(request):
    selected_date = get_selected_date(request)

    # Ensure that the selected date is valid (if necessary)
    if not selected_date:
        selected_date = timezone.now().date()  # Import timezone if you use it

    # Query departments with attendance counts
    departments = Department.objects.annotate(
        late_count=Count('employees', filter=Q(employees__attendance__arrival_status='late', employees__attendance__date=selected_date)),
        absent_count=Count('employees', filter=Q(employees__attendance__arrival_status='absent', employees__attendance__date=selected_date)),
        on_time_count=Count('employees', filter=Q(employees__attendance__arrival_status='ontime', employees__attendance__date=selected_date)),
        present_today_count=F('late_count') + F('on_time_count')  # Calculate present based on late and on-time counts
    )
        
    context = {
        "departments": departments,
        "default_date": selected_date,
    }
    
    return render(request, 'departments.html', context)



def add_department(request):
    if request.method == 'POST':
        department_name = request.POST.get('department_name')
        if department_name:
            Department.objects.create(name=department_name)
            messages.success(request, 'Department added successfully!')
            return redirect('departments')  # Redirect to the departments list or desired page
        else:
            messages.error(request, 'Department name cannot be empty.')

    return render(request, 'add_department.html')  # Render the form template



@login_required
def viewdepartment(request, department_id):
    department = Department.objects.get(id=department_id)
    selected_date = get_selected_date(request)
    
    employees = Employee.objects.filter(department_name=department)
    attendance_records = Attendance.objects.filter(employee__in=employees, date=selected_date)
   
    return render(request, 'viewdepartments.html', {
        'department': department,
        'employees': employees,
        'attendance_records': attendance_records,
        'default_date': selected_date,
    })



# def get_today_attendance(employee_id):

#     today = timezone.now().date()

#     attendance = Attendance.objects.filter(employee_id=employee_id, date=today)

#     if attendance.exists():

#         return attendance.first()

#     else:

#         return None
    
# @login_required
# def viewdepartment(request, department_id):
#     # Fetch the department based on the provided department_id
#     department = Department.objects.get(id=department_id)
    
#     # Get all employees associated with the department
#     employees = Employee.objects.filter(department_name_id=department_id)
    
#     # Initialize an empty dictionary to store attendance data
#     attendance_data = {}
    
#     # Loop through each employee and get their attendance for today
#     for employee in employees:

#         attendance = get_today_attendance(employee.id)

#         if attendance:

#             attendance_data[employee.id] = {

#                 'status': attendance.status,

#                 'time': attendance.time,

#             }

#         else:

#             attendance_data[employee.id] = {

#                 'status': 'not yet marked',

#                 'time': 'not yet marked',

#             }
    
#     # Render the template with the department, employees, and attendance data
#     return render(request, 'viewdepartments.html', {
#         'department': department,
#         'employees': employees,
#         'attendance_data': attendance_data,
#     })

