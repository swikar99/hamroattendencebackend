from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required.')
        email = self.normalize_email(email)
        # Auto-assign organization from email domain
        if 'organization' not in extra_fields or extra_fields.get('organization') is None:
            from apps.organizations.models import Organization
            org = Organization.get_by_email(email)
            if org:
                extra_fields['organization'] = org
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'superadmin')
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('superadmin', 'Super Admin'),
        ('org_admin',  'Org Admin'),
        ('hr_manager', 'HR Manager'),
        ('manager',    'Manager'),
        ('employee',   'Employee'),
        ('teacher',    'Teacher'),
        ('student',    'Student'),
    ]

    username      = None
    email         = models.EmailField(unique=True)
    organization  = models.ForeignKey(
        'organizations.Organization', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='members'
    )
    department    = models.ForeignKey(
        'organizations.Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='members'
    )
    manager       = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='direct_reports', help_text='Reporting manager'
    )
    role          = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    phone_number  = models.CharField(max_length=20, blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender        = models.CharField(max_length=1, choices=[('M','Male'),('F','Female'),('O','Other')], blank=True)
    address       = models.TextField(blank=True)
    joining_date  = models.DateField(null=True, blank=True)
    employee_id   = models.CharField(max_length=50, blank=True, unique=True, null=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    is_active     = models.BooleanField(default=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    objects         = CustomUserManager()

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['organization', 'role']),
        ]

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}>"

    @property
    def is_org_admin_or_above(self):
        return self.role in ('superadmin', 'org_admin')

    @property
    def is_manager_or_above(self):
        return self.role in ('superadmin', 'org_admin', 'hr_manager', 'manager')
