from django.db import models


class ReportJob(models.Model):
    STATUS_CHOICES = [
        ('pending',    'Pending'),
        ('processing', 'Processing'),
        ('done',       'Done'),
        ('failed',     'Failed'),
    ]
    TYPE_CHOICES = [
        ('daily',       'Daily Summary'),
        ('monthly',     'Monthly Summary'),
        ('department',  'Department-wise'),
        ('leave',       'Leave Report'),
        ('payroll',     'Payroll Timesheet'),
    ]

    requested_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.CASCADE, related_name='report_jobs'
    )
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.CASCADE, related_name='report_jobs'
    )
    report_type  = models.CharField(max_length=30, choices=TYPE_CHOICES)
    format       = models.CharField(max_length=10, choices=[('excel', 'Excel'), ('pdf', 'PDF')], default='excel')
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    parameters   = models.JSONField(default=dict, blank=True)
    file_path    = models.FileField(upload_to='reports/', null=True, blank=True)
    error        = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.report_type} — {self.organization} [{self.status}]"
