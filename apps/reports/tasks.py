import io
import logging
from celery import shared_task
from django.utils import timezone
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def generate_report_async(self, job_id):
    """Pick up a ReportJob and generate the file, saving it to the job record."""
    from apps.reports.models import ReportJob
    from apps.reports import generators
    from apps.organizations.models import Organization
    from datetime import date

    try:
        job = ReportJob.objects.get(pk=job_id)
    except ReportJob.DoesNotExist:
        logger.error("ReportJob %s not found", job_id)
        return

    job.status = 'processing'
    job.save(update_fields=['status'])

    try:
        org   = job.organization
        params = job.parameters
        fmt   = job.format

        if job.report_type == 'daily':
            target = date.fromisoformat(params['date'])
            data = (generators.generate_daily_excel(org, target)
                    if fmt == 'excel' else generators.generate_daily_pdf(org, target))
            ext  = 'xlsx' if fmt == 'excel' else 'pdf'
            name = f"daily_{target}_{org.id}.{ext}"

        elif job.report_type == 'monthly':
            year, month = int(params['year']), int(params['month'])
            data = generators.generate_monthly_excel(org, year, month)
            name = f"monthly_{year}_{month:02d}_{org.id}.xlsx"

        elif job.report_type == 'department':
            from datetime import date as dt
            start = date.fromisoformat(params['start_date'])
            end   = date.fromisoformat(params['end_date'])
            data  = generators.generate_department_excel(org, start, end)
            name  = f"dept_{start}_{end}_{org.id}.xlsx"

        elif job.report_type == 'payroll':
            year, month = int(params['year']), int(params['month'])
            data = generators.generate_payroll_excel(org, year, month)
            name = f"payroll_{year}_{month:02d}_{org.id}.xlsx"

        else:
            raise ValueError(f"Unknown report type: {job.report_type}")

        job.file_path.save(name, ContentFile(data), save=False)
        job.status       = 'done'
        job.completed_at = timezone.now()
        job.save(update_fields=['file_path', 'status', 'completed_at'])
        logger.info("ReportJob %s completed: %s", job_id, name)

    except Exception as exc:
        logger.exception("ReportJob %s failed: %s", job_id, exc)
        job.status = 'failed'
        job.error  = str(exc)
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'error', 'completed_at'])
        raise self.retry(exc=exc)
