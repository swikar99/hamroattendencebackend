from datetime import date
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from apps.accounts.permissions import IsHROrAbove
from .models import ReportJob
from .serializers import ReportJobSerializer
from . import generators
from .tasks import generate_report_async

_FILE_RESPONSE = OpenApiResponse(description='Excel or PDF file download')
_DATE_PARAM    = OpenApiParameter('date',  OpenApiTypes.DATE, description='Date (YYYY-MM-DD), default today')
_FORMAT_PARAM  = OpenApiParameter('format', str, enum=['excel', 'pdf'], description='Output format, default excel')
_YEAR_PARAM    = OpenApiParameter('year',  OpenApiTypes.INT, description='Year, default current year')
_MONTH_PARAM   = OpenApiParameter('month', OpenApiTypes.INT, description='Month (1-12), default current month')
_START_PARAM   = OpenApiParameter('start_date', OpenApiTypes.DATE, description='Start date (YYYY-MM-DD)', required=True)
_END_PARAM     = OpenApiParameter('end_date',   OpenApiTypes.DATE, description='End date (YYYY-MM-DD)',   required=True)


@extend_schema(tags=['Reports'])
@extend_schema_view(
    list=extend_schema(summary='List all report jobs'),
    retrieve=extend_schema(summary='Get report job status / download URL'),
)
class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List/retrieve report jobs and trigger new report generation.
    Supports both synchronous (small) and async (large) generation.
    """
    serializer_class      = ReportJobSerializer
    lookup_value_regex    = r'[0-9]+'
    permission_classes = [IsAuthenticated, IsHROrAbove]

    def get_queryset(self):
        return ReportJob.objects.filter(organization=self.request.user.organization)

    # ── Sync download helpers ─────────────────────────────────────────────────

    @extend_schema(summary='Download daily attendance report', parameters=[_DATE_PARAM, _FORMAT_PARAM], responses={200: _FILE_RESPONSE})
    @action(detail=False, methods=['get'])
    def daily(self, request):
        """
        GET /reports/daily/?date=YYYY-MM-DD&format=excel|pdf
        Streams the file directly for small one-off downloads.
        """
        date_str = request.query_params.get('date', str(date.today()))
        fmt      = request.query_params.get('format', 'excel')
        try:
            target = date.fromisoformat(date_str)
        except ValueError:
            return Response({'detail': 'Invalid date format. Use YYYY-MM-DD.'},
                            status=status.HTTP_400_BAD_REQUEST)

        org = request.user.organization
        if fmt == 'pdf':
            data         = generators.generate_daily_pdf(org, target)
            content_type = 'application/pdf'
            filename     = f"daily_{target}.pdf"
        else:
            data         = generators.generate_daily_excel(org, target)
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename     = f"daily_{target}.xlsx"

        resp = HttpResponse(data, content_type=content_type)
        resp['Content-Disposition'] = f'attachment; filename="{filename}"'
        return resp

    @extend_schema(summary='Download monthly attendance report (Excel)', parameters=[_YEAR_PARAM, _MONTH_PARAM], responses={200: _FILE_RESPONSE})
    @action(detail=False, methods=['get'])
    def monthly(self, request):
        """GET /reports/monthly/?year=YYYY&month=MM"""
        try:
            year  = int(request.query_params.get('year',  date.today().year))
            month = int(request.query_params.get('month', date.today().month))
        except ValueError:
            return Response({'detail': 'year and month must be integers.'},
                            status=status.HTTP_400_BAD_REQUEST)

        org  = request.user.organization
        data = generators.generate_monthly_excel(org, year, month)
        resp = HttpResponse(
            data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        resp['Content-Disposition'] = f'attachment; filename="monthly_{year}_{month:02d}.xlsx"'
        return resp

    @extend_schema(summary='Download department-wise report (Excel)', parameters=[_START_PARAM, _END_PARAM], responses={200: _FILE_RESPONSE})
    @action(detail=False, methods=['get'])
    def department(self, request):
        """GET /reports/department/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD"""
        try:
            start = date.fromisoformat(request.query_params['start_date'])
            end   = date.fromisoformat(request.query_params['end_date'])
        except (KeyError, ValueError):
            return Response({'detail': 'Provide start_date and end_date (YYYY-MM-DD).'},
                            status=status.HTTP_400_BAD_REQUEST)

        org  = request.user.organization
        data = generators.generate_department_excel(org, start, end)
        resp = HttpResponse(
            data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        resp['Content-Disposition'] = f'attachment; filename="department_{start}_{end}.xlsx"'
        return resp

    @extend_schema(summary='Download payroll timesheet (Excel)', parameters=[_YEAR_PARAM, _MONTH_PARAM], responses={200: _FILE_RESPONSE})
    @action(detail=False, methods=['get'])
    def payroll(self, request):
        """GET /reports/payroll/?year=YYYY&month=MM"""
        try:
            year  = int(request.query_params.get('year',  date.today().year))
            month = int(request.query_params.get('month', date.today().month))
        except ValueError:
            return Response({'detail': 'year and month must be integers.'},
                            status=status.HTTP_400_BAD_REQUEST)

        org  = request.user.organization
        data = generators.generate_payroll_excel(org, year, month)
        resp = HttpResponse(
            data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        resp['Content-Disposition'] = f'attachment; filename="payroll_{year}_{month:02d}.xlsx"'
        return resp

    # ── Async job trigger ─────────────────────────────────────────────────────

    @extend_schema(summary='Queue an async report generation job', request=ReportJobSerializer, responses={202: ReportJobSerializer})
    @action(detail=False, methods=['post'])
    def queue(self, request):
        """
        POST /reports/queue/
        Body: { "report_type": "monthly", "format": "excel", "parameters": {...} }
        Queues the job via Celery and returns the job id.
        """
        report_type = request.data.get('report_type')
        fmt         = request.data.get('format', 'excel')
        parameters  = request.data.get('parameters', {})

        if report_type not in dict(ReportJob.TYPE_CHOICES):
            return Response({'detail': f'Invalid report_type. Choices: {list(dict(ReportJob.TYPE_CHOICES).keys())}'},
                            status=status.HTTP_400_BAD_REQUEST)

        job = ReportJob.objects.create(
            requested_by = request.user,
            organization = request.user.organization,
            report_type  = report_type,
            format       = fmt,
            parameters   = parameters,
        )
        generate_report_async.delay(job.id)
        return Response(ReportJobSerializer(job, context={'request': request}).data,
                        status=status.HTTP_202_ACCEPTED)
