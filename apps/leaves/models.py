from django.db import models
from decimal import Decimal


class LeaveType(models.Model):
    GENDER_CHOICES = [('all','All'),('male','Male Only'),('female','Female Only')]

    organization           = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='leave_types')
    name                   = models.CharField(max_length=100)
    code                   = models.CharField(max_length=10, help_text='e.g. AL, SL, CL')
    description            = models.TextField(blank=True)
    max_days_per_year      = models.DecimalField(max_digits=5, decimal_places=1, default=15)
    is_paid                = models.BooleanField(default=True)
    requires_approval      = models.BooleanField(default=True)
    can_carry_forward      = models.BooleanField(default=False)
    max_carry_forward_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    applicable_gender      = models.CharField(max_length=10, choices=GENDER_CHOICES, default='all')
    min_days               = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal('0.5'), help_text='0.5 = half-day allowed')
    requires_document      = models.BooleanField(default=False)
    notice_days_required   = models.PositiveIntegerField(default=0)
    color                  = models.CharField(max_length=7, default='#007bff')
    is_active              = models.BooleanField(default=True)
    created_at             = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['organization', 'code']
        ordering = ['name']
        verbose_name = 'Leave Type'
        verbose_name_plural = 'Leave Types'

    def __str__(self):
        return f"{self.name} ({self.code})"


class LeaveBalance(models.Model):
    employee        = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='leave_balances')
    leave_type      = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='balances')
    year            = models.PositiveIntegerField()
    allocated       = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    used            = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    carried_forward = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    lapsed          = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['employee', 'leave_type', 'year']
        ordering = ['-year']
        verbose_name = 'Leave Balance'
        verbose_name_plural = 'Leave Balances'

    def __str__(self):
        return f"{self.employee.get_full_name()} — {self.leave_type.code} ({self.year})"

    @property
    def remaining(self):
        return max(Decimal('0'), self.allocated + self.carried_forward - self.used)

    @property
    def total_available(self):
        return self.allocated + self.carried_forward


class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('draft',            'Draft'),
        ('pending',          'Pending'),
        ('manager_approved', 'Manager Approved'),
        ('hr_approved',      'HR Approved'),
        ('approved',         'Approved'),
        ('rejected',         'Rejected'),
        ('cancelled',        'Cancelled'),
        ('revoked',          'Revoked'),
    ]
    HALF_DAY_CHOICES = [('morning','Morning'),('afternoon','Afternoon')]

    employee          = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='leave_requests')
    leave_type        = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='requests')
    start_date        = models.DateField()
    end_date          = models.DateField()
    total_days        = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    is_half_day       = models.BooleanField(default=False)
    half_day_period   = models.CharField(max_length=20, choices=HALF_DAY_CHOICES, blank=True)
    reason            = models.TextField()
    attachment        = models.FileField(upload_to='leave_attachments/', null=True, blank=True)
    status            = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    # Approval chain
    manager           = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='leave_manager_queue'
    )
    hr_manager        = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='leave_hr_queue'
    )
    final_approved_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='final_approved_leaves'
    )
    rejection_reason  = models.TextField(blank=True)
    is_emergency      = models.BooleanField(default=False)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Leave Request'
        verbose_name_plural = 'Leave Requests'

    def __str__(self):
        return f"{self.employee.get_full_name()} — {self.leave_type.code} ({self.start_date}→{self.end_date})"

    @property
    def duration_label(self):
        if self.is_half_day:
            return f"0.5 day ({self.half_day_period})"
        return f"{self.total_days} day(s)"

    def calculate_days(self, exclude_holidays=True, exclude_weekends=True):
        """Calculate business days between start and end dates."""
        from datetime import timedelta
        from apps.shifts.models import Holiday
        days = Decimal('0')
        current = self.start_date
        if exclude_holidays:
            holiday_dates = set(
                Holiday.objects.filter(
                    organization=self.employee.organization,
                    date__range=[self.start_date, self.end_date]
                ).values_list('date', flat=True)
            )
        else:
            holiday_dates = set()

        while current <= self.end_date:
            if exclude_weekends and current.weekday() >= 5:
                current += timedelta(days=1)
                continue
            if current in holiday_dates:
                current += timedelta(days=1)
                continue
            days += Decimal('1')
            current += timedelta(days=1)
        return days if not self.is_half_day else Decimal('0.5')


class LeaveApproval(models.Model):
    ACTION_CHOICES = [('approved','Approved'),('rejected','Rejected'),('forwarded','Forwarded')]

    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name='approvals')
    approver      = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='leave_approval_actions')
    level         = models.PositiveIntegerField(help_text='1=Manager, 2=HR, 3=Admin')
    action        = models.CharField(max_length=20, choices=ACTION_CHOICES)
    comments      = models.TextField(blank=True)
    acted_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['level', 'acted_at']
        verbose_name = 'Leave Approval'
        verbose_name_plural = 'Leave Approvals'

    def __str__(self):
        return f"{self.leave_request} — L{self.level}: {self.action}"
