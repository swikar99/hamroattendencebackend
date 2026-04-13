# Attendance Management System

A comprehensive Django REST Framework-based attendance management system with features for tracking employee attendance, managing leave requests, and generating reports.

## Features

- **Employee Management**: Create and manage employee profiles with departments and designations
- **Attendance Tracking**: Record daily attendance with check-in/check-out times
- **Leave Management**: Handle leave requests with approval workflow
- **Holiday Management**: Define company holidays
- **Reporting**: Generate attendance reports with statistics and analytics
- **Bulk Operations**: Mark attendance for multiple employees at once
- **Authentication**: Token-based and session authentication
- **Permissions**: Role-based access control with admin and user permissions

## Project Structure

```
hamro attendence/
├── manage.py
├── requirements.txt
├── attendanceSystem/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── attendance/
    ├── __init__.py
    ├── models.py
    ├── serializers.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    └── apps.py
```

## Installation

1. Clone or navigate to the project directory:
```bash
cd hamro\ attendence
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Apply migrations:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`

## API Endpoints

### Departments
- `GET /api/attendance/departments/` - List all departments
- `POST /api/attendance/departments/` - Create new department (Admin only)
- `GET /api/attendance/departments/{id}/` - Get department details
- `PUT /api/attendance/departments/{id}/` - Update department (Admin only)
- `DELETE /api/attendance/departments/{id}/` - Delete department (Admin only)

### Employees
- `GET /api/attendance/employees/` - List all employees
- `POST /api/attendance/employees/` - Create new employee (Admin only)
- `GET /api/attendance/employees/{id}/` - Get employee details
- `GET /api/attendance/employees/{id}/attendance_history/` - Get attendance history
- `GET /api/attendance/employees/{id}/stats/` - Get attendance statistics
- `PUT /api/attendance/employees/{id}/` - Update employee (Admin only)
- `DELETE /api/attendance/employees/{id}/` - Delete employee (Admin only)

### Attendance
- `GET /api/attendance/attendance/` - List all attendance records
- `POST /api/attendance/attendance/` - Create attendance record (Admin only)
- `GET /api/attendance/attendance/{id}/` - Get attendance details
- `POST /api/attendance/attendance/bulk_mark/` - Bulk mark attendance (Admin only)
- `GET /api/attendance/attendance/by_date/` - Get records by date
- `GET /api/attendance/attendance/by_department/` - Get records by department
- `PUT /api/attendance/attendance/{id}/` - Update attendance (Admin only)
- `DELETE /api/attendance/attendance/{id}/` - Delete attendance (Admin only)

### Leave Requests
- `GET /api/attendance/leave-requests/` - List all leave requests
- `POST /api/attendance/leave-requests/` - Create leave request
- `GET /api/attendance/leave-requests/{id}/` - Get leave request details
- `POST /api/attendance/leave-requests/{id}/approve/` - Approve leave (Admin only)
- `POST /api/attendance/leave-requests/{id}/reject/` - Reject leave (Admin only)
- `GET /api/attendance/leave-requests/pending/` - Get pending requests
- `GET /api/attendance/leave-requests/my_leaves/` - Get user's leave requests
- `PUT /api/attendance/leave-requests/{id}/` - Update leave request
- `DELETE /api/attendance/leave-requests/{id}/` - Delete leave request

### Holidays
- `GET /api/attendance/holidays/` - List all holidays
- `POST /api/attendance/holidays/` - Create holiday (Admin only)
- `GET /api/attendance/holidays/{id}/` - Get holiday details
- `GET /api/attendance/holidays/current_year/` - Get current year holidays
- `PUT /api/attendance/holidays/{id}/` - Update holiday (Admin only)
- `DELETE /api/attendance/holidays/{id}/` - Delete holiday (Admin only)

### Reports
- `GET /api/attendance/reports/` - List all reports
- `GET /api/attendance/reports/{id}/` - Get report details
- `POST /api/attendance/reports/generate/` - Generate attendance report

## Example Usage

### Create Department
```bash
curl -X POST http://localhost:8000/api/attendance/departments/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "IT", "description": "Information Technology"}'
```

### Create Employee
```bash
curl -X POST http://localhost:8000/api/attendance/employees/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user": 1,
    "employee_id": "EMP001",
    "department": 1,
    "designation": "Software Engineer",
    "phone_number": "9841234567",
    "joining_date": "2024-01-01",
    "status": "active"
  }'
```

### Mark Attendance
```bash
curl -X POST http://localhost:8000/api/attendance/attendance/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "employee": 1,
    "date": "2024-01-15",
    "status": "present",
    "check_in_time": "09:00:00",
    "check_out_time": "17:30:00"
  }'
```

### Request Leave
```bash
curl -X POST http://localhost:8000/api/attendance/leave-requests/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "leave_type": "casual",
    "start_date": "2024-02-01",
    "end_date": "2024-02-03",
    "reason": "Personal emergency"
  }'
```

### Bulk Mark Attendance
```bash
curl -X POST http://localhost:8000/api/attendance/attendance/bulk_mark/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "employee_id": "EMP001",
      "date": "2024-01-15",
      "status": "present",
      "check_in_time": "09:00:00",
      "check_out_time": "17:30:00"
    },
    {
      "employee_id": "EMP002",
      "date": "2024-01-15",
      "status": "absent"
    }
  ]'
```

### Generate Report
```bash
curl -X POST http://localhost:8000/api/attendance/reports/generate/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "EMP001",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "report_type": "monthly"
  }'
```

## Models

### Department
- name: CharField (unique)
- description: TextField
- created_at: DateTimeField
- updated_at: DateTimeField

### Employee
- user: OneToOneField (User)
- employee_id: CharField (unique)
- department: ForeignKey (Department)
- designation: CharField
- phone_number: CharField
- date_of_birth: DateField
- gender: CharField
- address: TextField
- joining_date: DateField
- status: CharField (active, inactive, on_leave)
- profile_photo: ImageField

### Attendance
- employee: ForeignKey (Employee)
- date: DateField
- status: CharField (present, absent, late, half_day, leave)
- check_in_time: TimeField
- check_out_time: TimeField
- notes: TextField
- marked_by: ForeignKey (User)

### LeaveRequest
- employee: ForeignKey (Employee)
- leave_type: CharField
- start_date: DateField
- end_date: DateField
- reason: TextField
- status: CharField (pending, approved, rejected, cancelled)
- approved_by: ForeignKey (User)

### Holiday
- name: CharField
- date: DateField
- description: TextField
- is_paid: BooleanField

### AttendanceReport
- employee: ForeignKey (Employee)
- report_type: CharField
- start_date: DateField
- end_date: DateField
- total_days: IntegerField
- present_days: IntegerField
- absent_days: IntegerField
- attendance_percentage: FloatField

## Authentication

The system uses Token Authentication. To get a token:

```bash
curl -X POST http://localhost:8000/api-token-auth/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

## Admin Interface

Access the admin panel at `http://localhost:8000/admin/` with your superuser credentials to:
- Manage users and employees
- View and edit attendance records
- Manage leave requests
- Configure holidays
- View reports

## Security Considerations

1. Change the `SECRET_KEY` in settings.py for production
2. Set `DEBUG = False` in production
3. Use environment variables for sensitive data
4. Configure ALLOWED_HOSTS appropriately
5. Use HTTPS in production
6. Implement proper CORS settings for frontend domains

## License

This project is open source and available under the MIT License.
# hamroattendencebackend
