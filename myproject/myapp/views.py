from django.http import HttpResponse
from django.shortcuts import render, redirect    
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from .models import Department,Employee, Attendance, CustomSchedule, OvertimeSetting
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
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.utils.timezone import now

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

def log_action(user, action_flag, obj, change_message):

    LogEntry.objects.log_action(
        user_id=user.id,
        content_type_id=ContentType.objects.get_for_model(obj).id,
        object_id=obj.id,
        object_repr=str(obj),
        action_flag=action_flag,
        change_message=change_message
    )




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
    
    overtime_setting = OvertimeSetting.objects.first()  # Assuming only one setting
    overtime_duration_hours = overtime_setting.overtime_duration_hours if overtime_setting else 3  # Default to 3 if not set
    overtime_window = time_out_dt + timedelta(hours=overtime_duration_hours)

    # Calculate half-gap time
    gap_time = time_out_dt - time_in_dt
    half_gap_time = time_in_dt + gap_time / 2  # Halfway point in datetime
    print(f"Time-in: {time_in}, Time-out: {time_out}, Half Gap Time: {half_gap_time.time()}")
    
    half_gap_time_str = half_gap_time.time().strftime('%H:%M')
    button_text = 'Log in'  # Default to Time In
    
    
    

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
                return render(request, 'checkin.html', {
    'absence_alert_message': 'You are marked absent',
    'employee_name': f"{employee.first_name} {employee.last_name}",
    'button_text': button_text,
    'half_gap_time': half_gap_time_str,  # Pass half_gap_time to the template
})


            # Save time-in and prevent re-checkin
            attendance.time_in = current_time
            attendance.save()
            return render(request, 'checkin.html', {
    'alert_message': 'Logged in successfully!',
    'employee_name': f"{employee.first_name} {employee.last_name}",
    'button_text': button_text,
    'half_gap_time': half_gap_time_str,  # Pass half_gap_time to the template
    
})


        # Prevent re-checkin if already checked in and before half_gap_time
        if attendance.time_in is not None and current_time_dt < half_gap_time:
             return render(request, 'checkin.html', {
        'already_checked_in_message': 'You have already logged in for today.',
        'employee_name': f"{employee.first_name} {employee.last_name}"
        
    })
             
        if attendance.time_out is not None:
            return render(request, 'checkin.html', {
        'already_timed_out_message': 'You have already logged out for today.',
        'employee_name': f"{employee.first_name} {employee.last_name}"
       
    })

        # Time-out logic
        if attendance.time_out is None and current_time_dt >= half_gap_time:
            overtime_window = time_out_dt + timedelta(hours=overtime_duration_hours)

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
        'timeout_alert_message': 'logout marked successfully!',
        'employee_name': f"{employee.first_name} {employee.last_name}",
        'button_text': button_text,
        'half_gap_time': half_gap_time_str,  # Pass half_gap_time to the template
    })
    # Render the checkin page if no form has been submitted
    return render(request, 'checkin.html', {
        'button_text': button_text,
        'half_gap_time': half_gap_time_str,  # Pass half_gap_time to the template
    })
        
        




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



def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_new_password = request.POST.get('confirm_new_password')
        employee = Employee.objects.get(employee_id=request.session.get('employee_id'))

        # Check if the current password matches
        if not check_password(current_password, employee.password):
            messages.warning(request, 'Current password is incorrect.')
            return redirect('employee-dashboard')  # Redirect to the dashboard

        # Check if the new passwords match
        if new_password != confirm_new_password:
            messages.warning(request, 'New passwords do not match.')
            return redirect('employee-dashboard')  # Redirect to the dashboard

        # Update the password
        employee.password = make_password(new_password)
        employee.save()

        messages.success(request, 'Password changed successfully!')
        return redirect('employee-dashboard')  # Redirect to the dashboard

    # If the request method is not POST, render the dashboard (or handle accordingly)
    return render(request, 'employee-dashboard.html')


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
        
        if Employee.objects.filter(employee_id=employee_id).exists():
            messages.error(request, f'Employee ID "{employee_id}" is already taken. Please use a unique ID.')
        
        else:
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
            log_action(
                request.user,
                CHANGE,  # Use DELETION for delete actions
                employee,  # Log the actual employee object
                f'Employee "{employee.first_name} {employee.last_name}" created successfully.'
        )
        

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
        "departments": departments,
       
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
            password = request.POST.get('password')
            if password:
                employee.password = make_password(password) 
            # Assign the retrieved department object to the employee
            employee.department_name = department
            
            # Save the updated employee instance
            
            employee.save()
            log_action(
            request.user,
            CHANGE,  # Use DELETION for delete actions
            employee,  # Log the actual employee object
            f'Employee "{employee.first_name} {employee.last_name}" has been edited.'
    )
            
            # Redirect after saving the employee
           

        except Department.DoesNotExist:
            # Handle case when the department ID is invalid
            return render(request, 'employeelist.html', {
                'employee': employee, 
                'departments': Department.objects.all(),
                'error_message': "Department does not exist.",
                
            })
    
    # If it's a GET request, render the form with the employee's existing data
    return render(request, 'employeelist.html', {
    'employees': Employee.objects.all(),  # Pass updated employee list
    'departments': Department.objects.all(),
   
})

    

@login_required
def delete_employee(request, employee_id):
    # Ensure the employee exists
    employee = Employee.objects.get(pk=employee_id)  # This is correct


    # Delete the employee
    employee.delete()
    log_action(
        request.user,
        CHANGE,  # Use DELETION for delete actions
        employee,  # Log the actual employee object
        f'Employee "{employee.first_name} {employee.last_name}" deleted.'
    )
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
    today = date.today()
    
    # Check if there is a schedule for today
    schedule_exists_today = CustomSchedule.objects.filter(date=today).exists()

    # Check if attendance has been marked for today
    attendance_exists_today = Attendance.objects.filter(date=today).exists()

    # Determine button visibility
    button_display = not (schedule_exists_today and attendance_exists_today)

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
                  
                # Log the action after creating or updating
                if created:
                    log_action(
                        request.user,
                        ADDITION,
                        custom_schedule,
                        f'Created an event for "{reason}" on {selected_date}.'
                        
                    )
                    alert_message = f'Custom schedule for "{reason}" set successfully on {selected_date}!'
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

        # Handle overtime duration update if form is submitted
        if 'overtime_duration' in request.POST:
            try:
                overtime_duration = int(request.POST.get('overtime_duration'))

                if overtime_duration < 1:
                    alert_message = 'Overtime duration must be at least 1 hour.'
                    alert_icon = 'error'
                else:
                    # Update the overtime setting or create a new one
                    overtime_setting = OvertimeSetting.objects.first()
                    if overtime_setting:
                        
                        # Capture the current overtime duration before updating
                        current_overtime_duration = overtime_setting.overtime_duration_hours
                        
                        overtime_setting.overtime_duration_hours = overtime_duration
                        overtime_setting.save()
                        log_action(request.user, CHANGE, overtime_setting, f'Updated overtime duration from {current_overtime_duration} to {overtime_duration} hours.')
                    else:
                        OvertimeSetting.objects.create(overtime_duration_hours=overtime_duration)
                    
                    alert_message = f'Overtime duration set to {overtime_duration} hours.'
                    alert_icon = 'success'
            except ValueError:
                alert_message = 'Invalid overtime duration provided.'
                alert_icon = 'error'

    # Fetch the current overtime setting (for display)
    overtime_setting = OvertimeSetting.objects.first()
    current_overtime_duration = overtime_setting.overtime_duration_hours if overtime_setting else 3  # Default to 3 hours

    # Render the schedule list with any alert messages
    return render(request, 'schedule_list.html', {
        'schedules': schedules,
        'alert_message': alert_message,
        'alert_icon': alert_icon,
        'overtime_duration': current_overtime_duration,
        'button_display': button_display,
        'today': today,
        'attendance_exists_today': attendance_exists_today,
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
                log_action(
                    request.user,
                    CHANGE,
                    schedule,
                    f'An event named "{reason}" in {selected_date} has been edited.'
                )

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
         # Log the deletion action
        log_action(
            request.user,
            CHANGE,  # Use CHANGE for deletion in this context
            schedule,
            f'Event "{schedule}" is deleted.'
        )
        return redirect('schedule_list')  # Redirect to the schedule list after deletion

    return render(request, 'confirm_delete.html', {'schedule': schedule})





# @login_required
# def admin_dashboard_view(request):
#     # Get today's date
#     today = timezone.now().astimezone(pytz.timezone('Asia/Manila')).date()
    
#     attendance_records = get_non_absent_employees()
    
    
#     print(f"Attendance records for today: {attendance_records}")
    
#     # Check if the attendance records contain any data
#     if not attendance_records.exists():
#         print("No attendance records found for today.")
#     else:
#         print(f"Found {attendance_records.count()} attendance records for today.")
#     context = {
#         'attendance_records': attendance_records
#     }
    
#     return render(request, 'admin_dashboard.html', context)




@login_required
def admin_dashboard_view(request):
    # Get today's date
    today = timezone.now().astimezone(pytz.timezone('Asia/Manila')).date()
    
    # Fetch attendance records
    attendance_records = get_non_absent_employees()
    
    print(f"Attendance records for today: {attendance_records}")
    
    # Check if the attendance records contain any data
    if not attendance_records.exists():
        print("No attendance records found for today.")
    else:
        print(f"Found {attendance_records.count()} attendance records for today.")
    
    # Get the superuser (replace with your superuser's username)
    superuser = User.objects.get(username='lei')  # Replace with your superuser's username
    print(superuser)
    
    # Get all log entries for the superuser in the last 24 hours
    recent_logs = LogEntry.objects.filter(user=superuser).order_by('-action_time')
    
    print(recent_logs)
    
    # Prepare the context
    context = {
        'attendance_records': attendance_records,
        'recent_logs': recent_logs,
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
            messages.warning(request, "Invalid username or password")
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
    date_str = request.GET.get('date', '')  # Get the date from query parameters
    if date_str:
        try:
            # Attempt to parse the date
            return timezone.datetime.fromisoformat(date_str).date()
        except ValueError:
            # If parsing fails, log the error and fall back to the current date
            return now().date()
    # If no date provided, default to today's date
    return now().date()

@login_required
def departments(request):
    selected_date = get_selected_date(request)

    # Ensure that the selected date is valid (if necessary)
    if not selected_date:
        selected_date = now().date()  # Import timezone if you use it

    # Query departments with attendance counts
    departments = Department.objects.annotate(
        late_count=Count('employees', filter=Q(employees__attendance__arrival_status='late', employees__attendance__date=selected_date)),
        absent_count=Count('employees', filter=Q(employees__attendance__arrival_status='absent', employees__attendance__date=selected_date)),
        on_time_count=Count('employees', filter=Q(employees__attendance__arrival_status='ontime', employees__attendance__date=selected_date)),
        present_today_count=F('late_count') + F('on_time_count')  # Calculate present based on late and on-time counts
    )
        
    context = {
        "departments": departments,
        "selected_date": selected_date.isoformat(),  # Ensure the selected date is passed as a string in YYYY-MM-DD format
        "today": timezone.now().date().isoformat()
    }
    
    return render(request, 'departments.html', context)



def add_department(request):
    if request.method == 'POST':
        department_name = request.POST.get('department_name', '').strip()  # Ensure the name is stripped of leading/trailing spaces
        if department_name:
            try:
                # Create a new department
                new_department = Department.objects.create(name=department_name)

                # Log the action
                log_action(
                    request.user,
                    ADDITION,  
                    new_department,  
                    f'New department "{new_department.name}" created.'
                )

                # Display a success message
                messages.success(request, 'Department created successfully.')
                return redirect('departments')  # Redirect to the departments list or desired page

            except Exception as e:
                # Handle any errors during creation
                messages.error(request, f'Error creating department: {e}')
        else:
            # Handle empty input
            messages.error(request, 'Department name cannot be empty.')

    # Render the form template if GET request or an error occurs
    return render(request, 'departments.html')



@login_required
def viewdepartment(request, department_id):
    department = Department.objects.get(id=department_id)
    selected_date = get_selected_date(request)
    
    # Filter attendance records for non-absent employees
    employees = Employee.objects.filter(department_name=department)
    attendance_records = Attendance.objects.filter(
        employee__in=employees, 
        date=selected_date
    ).exclude(arrival_status='absent')  # Exclude absent employees
    
    # Get a list of employees that are not absent
    non_absent_employees = employees.filter(id__in=attendance_records.values_list('employee', flat=True))

    return render(request, 'viewdepartments.html', {
        'department': department,
        'employees': non_absent_employees,  # Only show non-absent employees
        'attendance_records': attendance_records,
        'default_date': selected_date,
    })



def get_non_absent_employees(date=None):
    # If no date is provided, use today's date
    if not date:
        philippine_tz = pytz.timezone('Asia/Manila')
        date = timezone.now().astimezone(philippine_tz).date()

    # Fetch attendance records for today where the employee is not absent
    attendance_records = Attendance.objects.filter(date=date).exclude(arrival_status='absent')

    # Ensure that only employees with attendance records for the selected date are included
    non_absent_employees = attendance_records.values_list('employee', flat=True)
    
    # Return attendance records for non-absent employees
    return Attendance.objects.filter(employee__in=non_absent_employees, date=date)
