from django.http import HttpResponse
from django.shortcuts import render, redirect    
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from .models import Department,Employee, Attendance, CustomSchedule
from django.utils import timezone
import pytz
from django.db.models import Count, Q
from django.contrib.auth.hashers import make_password
from django.http import HttpResponseNotFound
from django.contrib import messages
from django.contrib.auth.hashers import check_password



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
                messages.error(request, "Invalid username or password.")
        except Employee.DoesNotExist:
            messages.error(request, "Invalid username or password.")

    return render(request, 'signin.html')






def employee_dashboard(request):
    print("Employee dashboard view accessed") 
    employee_id = request.session.get('employee_id')
    
    if not employee_id:
        return redirect('signin')
    # Assuming employee_id is being passed as a string
   
      # Fetch employee using get_object_or_404
    employee = Employee.objects.get( employee_id=employee_id)

    # Get the selected month from the request
    selected_month = request.GET.get('month')  # Example: '2023-10' for October 2023
    
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
    return render(request, 'employee_dashboard.html', {
        'employee': employee,
        'attendance_records': attendance_records,
        'selected_month': selected_month,
    })



@login_required
def signup(request):
    if request.method == 'POST':
        # Extract data from the form
        employee_id = request.POST['employeeId']
        first_name = request.POST['firstName']
        last_name = request.POST['lastName']
        username = request.POST['username']
        password = request.POST['password']  # Get the raw password
        department_id = request.POST['department_name']  # Assuming department is passed as ID

        # Create a new Employee instance with hashed password
        employee = Employee(
            employee_id=employee_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            password=make_password(password),  # Hash the password before saving
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


def custom_scheduling(request):
    if request.method == 'POST':
        selected_date = request.POST.get('selected_date')
        custom_timein = request.POST.get('custom_timein')
        custom_timeout = request.POST.get('custom_timeout')  # Ensure custom_timeout is also passed
        reason = request.POST.get('reason')

        # Ensure both time-in and time-out are provided
        if selected_date and custom_timein and custom_timeout:
            time_in = timezone.datetime.strptime(custom_timein, '%H:%M').time()
            time_out = timezone.datetime.strptime(custom_timeout, '%H:%M').time()

            # Create or update the schedule for the specified date
            custom_schedule, created = CustomSchedule.objects.update_or_create(
                date=selected_date,
                defaults={'time_in': time_in, 'time_out': time_out, 'reason': reason}
            )

            alert_message = 'Custom schedule set successfully!'
            if not created:
                alert_message = 'Custom schedule updated successfully!'

            return render(request, 'custom_scheduling.html', {'alert_message': alert_message})

    return render(request, 'custom_scheduling.html')
        
        
        
        
        
        
        
        


def checkin(request):
    if request.method == 'POST':
        employee_input = request.POST.get('employee_input')
        print(f"Employee Input: {employee_input}")

        # Find the employee by employee_id or first_name and last_name
        try:
            employee = Employee.objects.get(employee_id=employee_input)
        except Employee.DoesNotExist:
            try:
                first_name, last_name = employee_input.split()
                employee = Employee.objects.get(first_name__iexact=first_name, last_name__iexact=last_name)
            except (Employee.DoesNotExist, ValueError):
                return HttpResponse("Employee not found.", status=404)

        # Get current date and time in Philippine timezone
        now_utc = timezone.now()
        philippine_tz = pytz.timezone('Asia/Manila')
        now_philippine = now_utc.astimezone(philippine_tz)
        current_time = now_philippine.time()
        current_date = now_philippine.date()

        # Default time-in and time-out if no custom schedule
        default_time_in = timezone.datetime.strptime('08:10', '%H:%M').time()
        default_time_out = timezone.datetime.strptime('18:10', '%H:%M').time()

        # Check attendance record for today
        attendance, created = Attendance.objects.get_or_create(employee=employee, date=current_date)

        # Check for custom schedule
        try:
            custom_schedule = CustomSchedule.objects.get(date=current_date)
            time_in = custom_schedule.time_in
            time_out = custom_schedule.time_out
        except CustomSchedule.DoesNotExist:
            # Use default times if no custom schedule is found
            time_in = default_time_in
            time_out = default_time_out

        # Calculate the gap between time_in and time_out, then find the half-gap time
        time_in_dt = timezone.datetime.combine(current_date, time_in)
        time_out_dt = timezone.datetime.combine(current_date, time_out)
        gap_time = time_out_dt - time_in_dt
        half_gap_time = time_in_dt + gap_time / 2  # Half-gap time (5 hours after time_in)
        half_gap_time = half_gap_time.time()  # Convert to time object

        print(f"Time-in: {time_in}, Time-out: {time_out}")
        print(f"Half Gap Time: {half_gap_time}")

        # If the employee hasn't marked their time-in and it's past the 5-hour gap (absent status)
        if attendance.time_in is None and current_time >= half_gap_time:
            attendance.arrival_status = 'absent'
            attendance.save()
            return render(request, 'checkin.html', {'alert_message': 'You are marked as absent for today. Time-in period has passed.'})

        # If the employee has already marked their time-in and it's within the first 5-hour gap
        if attendance.time_in is not None:
            if current_time < half_gap_time:
                return HttpResponse("You have already marked your time-in for today.", status=400)
            

        # If it's before the half-gap time and the employee hasn't marked their time-in yet
        if current_time < half_gap_time and attendance.time_in is None:
            if created:
                if current_time < time_in:  # Check-in before time_in (ontime)
                    attendance.arrival_status = 'ontime'
                elif current_time >= time_in and current_time < time_out:  # Late check-in
                    attendance.arrival_status = 'late'
                attendance.time_in = current_time  # Set time_in on first attendance mark
                attendance.save()
                return render(request, 'checkin.html', {'alert_message': 'Attendance marked successfully!'})
            else:
                return HttpResponse("You have already marked your attendance for today.", status=400)

        # After the 5-hour gap, the employee should now only be able to mark time-out
        if current_time >= half_gap_time:
            if attendance.time_in is not None and attendance.time_out is None:
                attendance.time_out = current_time

                # Determine the timeout status (ontime, overtime, left early, etc.)
                if current_time >= time_out:
                    attendance.timeout_status = 'ontime'  # Employee leaves at or after the expected time
                elif current_time < time_out:
                    attendance.timeout_status = 'overtime'  # Employee stays beyond expected time
                elif current_time < half_gap_time:  # Employee left before the expected time (early)
                    attendance.timeout_status = 'left early'  # Employee leaves before the expected time
                attendance.save()
                return render(request, 'checkin.html', {'alert_message': 'Time-out marked successfully!'})
            else:
                return HttpResponse("You have already marked your time-out for today.", status=400)

    return render(request, 'checkin.html')









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
            return HttpResponse("Invalid login credentials. Please try again.")
    
    if request.user.is_authenticated:
        return redirect('admin_dashboard')

    return render(request, 'login.html')









def employeelist(request):
    search_query = request.GET.get('search', '')
    if search_query:
        employee = Employee.objects.filter(
            Q(employee_id__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(employee__Department_name__icontains=search_query)
            
            
        )
    else:
        employee = Employee.objects.all()

    context = {
        "employee": employee
    }
    return render(request, 'employeelist.html', context)


@login_required
def view_employee(request, employee_id):
    # Assuming employee_id is being passed as a string
    try:
        # Fetch employee by employee_id (which is a CharField)
        employee = Employee.objects.get(employee_id=employee_id)
    except Employee.DoesNotExist:
        return HttpResponseNotFound("Employee not found.")
    # Get the selected month from the request
    selected_month = request.GET.get('month')  # Example: '2023-10' for October 2023
    
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

    departments = Department.objects.annotate(
        late_count=Count('employees', filter=Q(employees__attendance__arrival_status='late', employees__attendance__date=selected_date)),
        absent_count=Count('employees', filter=Q(employees__attendance__arrival_status='absent', employees__attendance__date=selected_date)),
        on_time_count=Count('employees', filter=Q(employees__attendance__arrival_status='ontime', employees__attendance__date=selected_date))
    )
    
    context = {
        "departments": departments,
        "default_date": selected_date,
    }
    return render(request, 'departments.html', context)

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

