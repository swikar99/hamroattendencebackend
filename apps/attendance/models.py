from django.db import models
from decimal import Decimal
from datetime import datetime, date as date_type, timedelta


def _get_org_settings(org):
    try:
        return org.settings
    except Exception:
        return None


class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('present',  'Present'),
        ('absent',   'Absent'),
        ('late',     'Late'),
        ('half_day', 'Half Day'),
        ('on_leave', 'On Leave'),
        ('holiday',  'Holiday'),
        ('weekend',  'Weekend'),
    ]
    METHOD_CHOICES = [
        ('manual',    'Manual'),
        ('qr',        'QR Code'),
        ('biometric', 'Biometric'),
        ('geo',       'Geo-fence'),
        ('face',      'Face ID'),
    ]

    employee           = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='attendance_records')
    organization       = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='attendance_records')
    date               = models.DateField()
    shift              = models.ForeignKey('shifts.Shift', on_delete=models.SET_NULL, null=True, blank=True)

    # Check-in
    check_in_time      = models.TimeField(null=True, blank=True)
    check_in_method    = models.CharField(max_length=20, choices=METHOD_CHOICES, blank=True)
    check_in_location  = models.CharField(max_length=100, blank=True, help_text='lat,lon string')
    check_in_device    = models.CharField(max_length=100, blank=True)
    check_in_photo     = models.ImageField(upload_to='attendance_photos/', null=True, blank=True)

    # Check-out
    check_out_time     = models.TimeField(null=True, blank=True)
    check_out_method   = models.CharField(max_length=20, choices=METHOD_CHOICES, blank=True)
    check_out_location = models.CharField(max_length=100, blank=True)
    check_out_device   = models.CharField(max_length=100, blank=True)

    # Computed
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default='absent')
    working_hours      = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overtime_hours     = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_late            = models.BooleanField(default=False)
    late_minutes       = models.PositiveIntegerField(default=0)
    is_half_day        = models.BooleanField(default=False)

    notes              = models.TextField(blank=True)
    marked_by          = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='marked_attendances'
    )
    is_regularized     = models.BooleanField(default=False)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['employee', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['organization', 'date']),
            models.Index(fields=['status']),
        ]
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'

    def __str__(self):
        return f"{self.employee.get_full_name()} — {self.date} ({self.status})"

    def _compute_working_hours(self):
        if not (self.check_in_time and self.check_out_time):
            return Decimal('0')
        dt_in  = datetime.combine(date_type.today(), self.check_in_time)
        dt_out = datetime.combine(date_type.today(), self.check_out_time)
        if dt_out < dt_in:
            dt_out += timedelta(days=1)  # night shift crossover
        hours = (dt_out - dt_in).total_seconds() / 3600
        # Deduct break
        if self.shift:
            hours -= self.shift.break_minutes / 60
        return Decimal(str(max(0, round(hours, 2))))

    def _compute_late_minutes(self):
        if not (self.shift and self.check_in_time):
            return 0
        scheduled = datetime.combine(date_type.today(), self.shift.start_time)
        actual    = datetime.combine(date_type.today(), self.check_in_time)
        grace     = self.shift.grace_period_minutes
        diff      = (actual - scheduled).total_seconds() / 60
        return max(0, int(diff - grace))

    def save(self, *args, **kwargs):
        self.working_hours = self._compute_working_hours()
        self.late_minutes  = self._compute_late_minutes()
        self.is_late       = self.late_minutes > 0

        if self.working_hours > 0 and self.status not in ('on_leave', 'holiday', 'weekend'):
            settings = _get_org_settings(self.organization)
            half_h  = settings.half_day_hours if settings else Decimal('4.0')
            full_h  = settings.overtime_threshold_hours if settings else Decimal('8.0')

            if self.working_hours < half_h:
                self.status = 'absent'
                self.is_half_day = False
            elif self.working_hours < full_h:
                self.status = 'half_day'
                self.is_half_day = True
            else:
                self.status = 'late' if self.is_late else 'present'
                self.is_half_day = False

            self.overtime_hours = max(Decimal('0'), self.working_hours - full_h)

        super().save(*args, **kwargs)


class AttendanceRegularization(models.Model):
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    employee            = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='regularization_requests')
    attendance_record   = models.ForeignKey(AttendanceRecord, on_delete=models.CASCADE, related_name='regularizations')
    requested_check_in  = models.TimeField(null=True, blank=True)
    requested_check_out = models.TimeField(null=True, blank=True)
    reason              = models.TextField()
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by         = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_regularizations'
    )
    reviewed_at         = models.DateTimeField(null=True, blank=True)
    rejection_reason    = models.TextField(blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Attendance Regularization'
        verbose_name_plural = 'Attendance Regularizations'

    def __str__(self):
        return f"{self.employee.get_full_name()} — {self.attendance_record.date} ({self.status})"
