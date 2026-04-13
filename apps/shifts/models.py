from django.db import models


class Shift(models.Model):
    TYPE_CHOICES = [
        ('fixed',    'Fixed'),
        ('rotating', 'Rotating'),
        ('flexible', 'Flexible'),
    ]

    organization         = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='shifts')
    name                 = models.CharField(max_length=100)
    type                 = models.CharField(max_length=20, choices=TYPE_CHOICES, default='fixed')
    start_time           = models.TimeField()
    end_time             = models.TimeField()
    grace_period_minutes = models.PositiveIntegerField(default=15, help_text='Minutes after start before marked late')
    break_minutes        = models.PositiveIntegerField(default=60)
    working_days         = models.JSONField(default=list, help_text='["mon","tue","wed","thu","fri"]')
    is_night_shift       = models.BooleanField(default=False)
    total_hours          = models.DecimalField(max_digits=4, decimal_places=2, default=8.0)
    is_active            = models.BooleanField(default=True)
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['organization', 'name']
        ordering = ['name']
        verbose_name = 'Shift'
        verbose_name_plural = 'Shifts'

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')}–{self.end_time.strftime('%H:%M')})"


class ShiftAssignment(models.Model):
    """Assign a shift to an employee for a date range."""
    employee       = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='shift_assignments')
    shift          = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='assignments')
    effective_from = models.DateField()
    effective_to   = models.DateField(null=True, blank=True, help_text='Null = indefinite current assignment')
    created_by     = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_shift_assignments'
    )
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-effective_from']
        verbose_name = 'Shift Assignment'
        verbose_name_plural = 'Shift Assignments'

    def __str__(self):
        return f"{self.employee} → {self.shift.name} from {self.effective_from}"


class Roster(models.Model):
    """Per-day shift override (supersedes ShiftAssignment for that date)."""
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='rosters')
    employee     = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='rosters')
    date         = models.DateField()
    shift        = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='rosters')
    notes        = models.TextField(blank=True)
    created_by   = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_rosters'
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['organization', 'employee', 'date']
        ordering = ['date']
        verbose_name = 'Roster'
        verbose_name_plural = 'Rosters'

    def __str__(self):
        return f"{self.employee.get_full_name()} — {self.date} — {self.shift.name}"


class Holiday(models.Model):
    TYPE_CHOICES = [
        ('national', 'National Holiday'),
        ('custom',   'Organization Holiday'),
    ]

    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='holidays')
    name         = models.CharField(max_length=100)
    date         = models.DateField()
    type         = models.CharField(max_length=20, choices=TYPE_CHOICES, default='custom')
    is_paid      = models.BooleanField(default=True)
    description  = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['organization', 'date']
        ordering = ['date']
        verbose_name = 'Holiday'
        verbose_name_plural = 'Holidays'

    def __str__(self):
        return f"{self.name} — {self.date}"
