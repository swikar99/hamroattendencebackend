from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification(self, recipient_id, title, message, notif_type='system',
                      reference_id=None, data=None):
    """Create an in-app notification record asynchronously."""
    try:
        from apps.notifications.models import Notification
        from apps.accounts.models import CustomUser

        recipient = CustomUser.objects.get(pk=recipient_id)
        Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            type=notif_type,
            reference_id=reference_id,
            data=data or {},
        )
        logger.info("Notification created for user %s: %s", recipient_id, title)
    except Exception as exc:
        logger.warning("send_notification failed (attempt %s): %s", self.request.retries, exc)
        raise self.retry(exc=exc)


@shared_task
def send_bulk_notification(recipient_ids, title, message, notif_type='system', data=None):
    """Send the same notification to multiple recipients."""
    for rid in recipient_ids:
        send_notification.delay(rid, title, message, notif_type, data=data)


@shared_task
def cleanup_old_notifications(days=30):
    """Delete read notifications older than `days` days."""
    from django.utils import timezone
    from datetime import timedelta
    from apps.notifications.models import Notification

    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = Notification.objects.filter(is_read=True, created_at__lt=cutoff).delete()
    logger.info("Cleaned up %d old notifications", deleted)
    return deleted
