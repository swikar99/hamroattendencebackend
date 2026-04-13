from django.db import models


class Notification(models.Model):
    TYPE_CHOICES = [
        ('leave_requested',         'Leave Requested'),
        ('leave_approved',          'Leave Approved'),
        ('leave_rejected',          'Leave Rejected'),
        ('check_in',                'Check In'),
        ('check_out',               'Check Out'),
        ('regularization_request',  'Regularization Request'),
        ('regularization_approved', 'Regularization Approved'),
        ('regularization_rejected', 'Regularization Rejected'),
        ('shift_assigned',          'Shift Assigned'),
        ('system',                  'System'),
    ]

    recipient    = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='notifications')
    title        = models.CharField(max_length=200)
    message      = models.TextField()
    type         = models.CharField(max_length=50, choices=TYPE_CHOICES, default='system')
    is_read      = models.BooleanField(default=False)
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    data         = models.JSONField(default=dict, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['recipient', 'is_read'])]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"[{self.type}] {self.recipient.get_full_name()} — {self.title}"
