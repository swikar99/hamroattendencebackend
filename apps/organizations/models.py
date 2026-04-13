from django.db import models


class Organization(models.Model):
    TYPE_CHOICES = [
        ('school',      'School'),
        ('college',     'College'),
        ('company',     'Company'),
        ('factory',     'Factory'),
        ('bank',        'Bank'),
        ('hospital',    'Hospital'),
        ('ngo',         'NGO'),
        ('government',  'Government'),
        ('other',       'Other'),
    ]

    name         = models.CharField(max_length=200)
    type         = models.CharField(max_length=20, choices=TYPE_CHOICES, default='company')
    email        = models.EmailField(blank=True)
    email_domain = models.CharField(
        max_length=100, unique=True, null=True, blank=True,
        help_text='Users with this email domain auto-join this org'
    )
    phone        = models.CharField(max_length=20, blank=True)
    address      = models.TextField(blank=True)
    logo         = models.ImageField(upload_to='org_logos/', null=True, blank=True)
    head_name    = models.CharField(max_length=200, blank=True, help_text='CEO/Principal/Director')
    established  = models.PositiveIntegerField(null=True, blank=True)
    timezone     = models.CharField(max_length=50, default='Asia/Kathmandu')
    currency     = models.CharField(max_length=3, default='NPR')
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    @classmethod
    def get_by_email(cls, email: str):
        try:
            domain = email.split('@')[1].lower()
            return cls.objects.get(email_domain=domain, is_active=True)
        except (IndexError, cls.DoesNotExist):
            return None

    @property
    def is_school_type(self):
        return self.type in ('school', 'college')


class OrganizationSettings(models.Model):
    organization             = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='settings')
    # Work schedule defaults
    default_work_start       = models.TimeField(default='09:00')
    default_work_end         = models.TimeField(default='18:00')
    work_days                = models.JSONField(default=list, help_text='["mon","tue","wed","thu","fri"]')
    grace_period_minutes     = models.PositiveIntegerField(default=15)
    half_day_hours           = models.DecimalField(max_digits=4, decimal_places=1, default=4.0)
    overtime_threshold_hours = models.DecimalField(max_digits=4, decimal_places=1, default=8.0)
    # Leave settings
    leave_year_start_month   = models.PositiveIntegerField(default=1, help_text='Month when leave year resets (1=Jan)')
    # Check-in methods
    allow_manual_checkin     = models.BooleanField(default=True)
    allow_qr_checkin         = models.BooleanField(default=True)
    allow_biometric_checkin  = models.BooleanField(default=False)
    allow_geo_checkin        = models.BooleanField(default=False)
    geo_fence_radius_meters  = models.PositiveIntegerField(default=100)
    office_latitude          = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    office_longitude         = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    # Payroll
    pay_period               = models.CharField(
        max_length=20,
        choices=[('monthly','Monthly'),('biweekly','Bi-weekly'),('weekly','Weekly')],
        default='monthly'
    )

    class Meta:
        verbose_name = 'Organization Settings'
        verbose_name_plural = 'Organization Settings'

    def __str__(self):
        return f"Settings — {self.organization.name}"


class Department(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='departments')
    name         = models.CharField(max_length=100)
    description  = models.TextField(blank=True)
    manager      = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_departments'
    )
    parent       = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_departments'
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['organization', 'name']
        ordering = ['name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

    def __str__(self):
        return f"{self.name} — {self.organization.name}"


# School-specific
class AcademicYear(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='academic_years')
    name         = models.CharField(max_length=20)
    start_date   = models.DateField()
    end_date     = models.DateField()
    is_current   = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']
        unique_together = ['organization', 'name']

    def __str__(self):
        return f"{self.name} — {self.organization.name}"

    def save(self, *args, **kwargs):
        if self.is_current:
            AcademicYear.objects.filter(organization=self.organization, is_current=True).update(is_current=False)
        super().save(*args, **kwargs)


class Class(models.Model):
    organization  = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='classes')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='classes', null=True, blank=True)
    name          = models.CharField(max_length=50)
    order         = models.PositiveIntegerField(default=0)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']
        unique_together = ['organization', 'academic_year', 'name']

    def __str__(self):
        return f"{self.name} — {self.organization.name}"


class Section(models.Model):
    grade        = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='sections')
    name         = models.CharField(max_length=10)
    max_students = models.PositiveIntegerField(default=40)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ['grade', 'name']

    def __str__(self):
        return f"{self.grade.name} - {self.name}"

    @property
    def student_count(self):
        return self.students.filter(status='active').count()


class Subject(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='subjects')
    name         = models.CharField(max_length=100)
    code         = models.CharField(max_length=20, blank=True)
    description  = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ['organization', 'code']

    def __str__(self):
        return f"{self.name} ({self.code})" if self.code else self.name


class Student(models.Model):
    STATUS_CHOICES = [('active','Active'),('inactive','Inactive'),('graduated','Graduated'),('transferred','Transferred')]
    GENDER_CHOICES = [('M','Male'),('F','Female'),('O','Other')]

    user           = models.OneToOneField('accounts.CustomUser', on_delete=models.CASCADE, related_name='student_profile')
    roll_number    = models.CharField(max_length=20, blank=True)
    organization   = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='students')
    section        = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    date_of_birth  = models.DateField(null=True, blank=True)
    gender         = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    blood_group    = models.CharField(max_length=5, blank=True)
    address        = models.TextField(blank=True)
    parent_name    = models.CharField(max_length=200, blank=True)
    parent_phone   = models.CharField(max_length=20, blank=True)
    parent_email   = models.EmailField(blank=True)
    admission_date = models.DateField(null=True, blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['roll_number']
        unique_together = ['organization', 'roll_number']

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.roll_number})"

    def save(self, *args, **kwargs):
        if not self.roll_number:
            from datetime import date
            year = date.today().year
            prefix = f"STU{self.organization_id}{year}-"
            last = Student.objects.filter(roll_number__startswith=prefix).order_by('roll_number').values_list('roll_number', flat=True).last()
            seq = int(last.split('-')[-1]) + 1 if last else 1
            self.roll_number = f"{prefix}{seq:04d}"
        super().save(*args, **kwargs)
