"""
Seed script for the new multi-app attendance system.
Run: python3 manage.py shell < init_data.py
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendanceSystem.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, Department, OrganizationSettings
from apps.shifts.models import Shift, ShiftAssignment

User = get_user_model()

# ── 1. Superadmin ──────────────────────────────────────────────────────────────
if not User.objects.filter(email='admin@hamro.com').exists():
    User.objects.create_superuser(
        email='admin@hamro.com', password='Admin@1234',
        first_name='Super', last_name='Admin', role='superadmin',
    )
    print("Created superadmin: admin@hamro.com / Admin@1234")

# ── 2. School org ──────────────────────────────────────────────────────────────
school, _ = Organization.objects.get_or_create(
    name='Sunrise English School',
    defaults=dict(type='school', email_domain='sunriseschool.edu',
                  phone='01-4123456', address='Kathmandu, Nepal', head_name='Ram Sharma'),
)
OrganizationSettings.objects.get_or_create(organization=school)
dept_s, _ = Department.objects.get_or_create(name='Teaching Staff', organization=school)

# School org_admin
admin_s, created = User.objects.get_or_create(
    email='principal@sunriseschool.edu',
    defaults=dict(first_name='Anita', last_name='Shrestha', role='org_admin',
                  organization=school, department=dept_s, is_active=True),
)
if created:
    admin_s.set_password('School@1234')
    admin_s.save()
    print(f"Created school admin: {admin_s.email}")

# School employees
school_staff = [
    ('teacher1@sunriseschool.edu', 'Bikash',  'Karki',    'teacher'),
    ('teacher2@sunriseschool.edu', 'Sunita',  'Thapa',    'teacher'),
    ('teacher3@sunriseschool.edu', 'Roshan',  'Gurung',   'teacher'),
    ('hr@sunriseschool.edu',       'Puja',    'Maharjan', 'hr_manager'),
]
for email, fn, ln, role in school_staff:
    u, created = User.objects.get_or_create(
        email=email,
        defaults=dict(first_name=fn, last_name=ln, role=role,
                      organization=school, department=dept_s, is_active=True),
    )
    if created:
        u.set_password('Staff@1234')
        u.save()
        print(f"  Created {role}: {email}")

# ── 3. Company org ─────────────────────────────────────────────────────────────
company, _ = Organization.objects.get_or_create(
    name='Tech Corp Pvt. Ltd.',
    defaults=dict(type='company', email_domain='techcorp.com',
                  phone='01-5678901', address='Lalitpur, Nepal', head_name='Sanjay Joshi'),
)
OrganizationSettings.objects.get_or_create(organization=company)
dept_eng, _ = Department.objects.get_or_create(name='Engineering',  organization=company)
dept_hr,  _ = Department.objects.get_or_create(name='HR',           organization=company)
dept_ops, _ = Department.objects.get_or_create(name='Operations',   organization=company)

admin_c, created = User.objects.get_or_create(
    email='ceo@techcorp.com',
    defaults=dict(first_name='Suresh', last_name='Joshi', role='org_admin',
                  organization=company, department=dept_ops, is_active=True),
)
if created:
    admin_c.set_password('Corp@1234')
    admin_c.save()
    print(f"Created company admin: {admin_c.email}")

company_staff = [
    ('eng1@techcorp.com', 'Anil',    'Basnet',  'employee',   dept_eng),
    ('eng2@techcorp.com', 'Priya',   'Koirala', 'employee',   dept_eng),
    ('eng3@techcorp.com', 'Deepak',  'Rai',     'employee',   dept_eng),
    ('mgr@techcorp.com',  'Manish',  'Pandey',  'manager',    dept_eng),
    ('hr1@techcorp.com',  'Sangita', 'Tamang',  'hr_manager', dept_hr),
    ('hr2@techcorp.com',  'Kabita',  'Lama',    'employee',   dept_hr),
]
for email, fn, ln, role, dept in company_staff:
    u, created = User.objects.get_or_create(
        email=email,
        defaults=dict(first_name=fn, last_name=ln, role=role,
                      organization=company, department=dept, is_active=True),
    )
    if created:
        u.set_password('Staff@1234')
        u.save()
        print(f"  Created {role}: {email}")

# ── 4. Default shifts ─────────────────────────────────────────────────────────
day_shift, _ = Shift.objects.get_or_create(
    name='Day Shift', organization=company,
    defaults=dict(type='fixed', start_time='09:00', end_time='17:00',
                  working_days=[0,1,2,3,4], grace_period_minutes=15, break_minutes=60),
)
school_shift, _ = Shift.objects.get_or_create(
    name='School Day', organization=school,
    defaults=dict(type='fixed', start_time='10:00', end_time='16:00',
                  working_days=[0,1,2,3,4], grace_period_minutes=10, break_minutes=30),
)
print("\nDefault shifts created.")
print("\n─── Seed complete ───────────────────────────────────────")
print("Superadmin:      admin@hamro.com        / Admin@1234")
print("School admin:    principal@sunriseschool.edu / School@1234")
print("Company admin:   ceo@techcorp.com       / Corp@1234")
print("Staff password:  Staff@1234")
print("API docs:        http://localhost:8000/api/docs/")
