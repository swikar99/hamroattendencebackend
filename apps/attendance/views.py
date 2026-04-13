from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from datetime import date, datetime, timedelta
from decimal import Decimal

from .models import AttendanceRecord, AttendanceRegularization
from .serializers import (
    AttendanceRecordSerializer, CheckInSerializer, CheckOutSerializer,
    BulkAttendanceSerializer, AttendanceRegularizationSerializer
)
from apps.accounts.permissions import IsManagerOrAbove, IsHROrAbove, IsSameOrg, IsOwnerOrManagerAbove


def _org(request):
    return request.user.organization


def _get_active_shift(employee, for_date):
    """Return the employee's shift for a specific date (roster override → shift assignment → None)."""
    from apps.shifts.models import Roster, ShiftAssignment
    # 1. Check roster override
    roster = Roster.objects.filter(employee=employee, date=for_date).select_related('shift').first()
    if roster:
        return roster.shift
    # 2. Check shift assignment
    assignment = ShiftAssignment.objects.filter(
        employee=employee,
        effective_from__lte=for_date,
    ).filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=for_date)
    ).order_by('-effective_from').first()
    return assignment.shift if assignment else None


def _validate_geo(org, location_str):
    """Validate that the check-in location is within geo-fence radius. Returns (ok, message)."""
    try:
        settings = org.settings
    except Exception:
        return True, ''
    if not settings.allow_geo_checkin:
        return True, ''
    if not (settings.office_latitude and settings.office_longitude):
        return True, ''
    try:
        from geopy.distance import geodesic
        lat, lon = map(float, location_str.split(','))
        office   = (float(settings.office_latitude), float(settings.office_longitude))
        actual   = (lat, lon)
        dist     = geodesic(office, actual).meters
        if dist > settings.geo_fence_radius_meters:
            return False, f"You are {dist:.0f}m from the office (allowed: {settings.geo_fence_radius_meters}m)."
    except Exception as e:
        return False, f"Invalid location data: {e}"
    return True, ''


class AttendanceRecordViewSet(viewsets.ModelViewSet):
    serializer_class   = AttendanceRecordSerializer
    permission_classes = [IsAuthenticated, IsSameOrg]
    queryset           = AttendanceRecord.objects.all()
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['employee__first_name', 'employee__last_name', 'employee__employee_id']
    ordering_fields    = ['date', 'check_in_time']

    def get_queryset(self):
        org = _org(self.request)
        qs = AttendanceRecord.objects.filter(
            organization=org
        ).select_related('employee', 'shift', 'marked_by') if org else AttendanceRecord.objects.none()

        emp_id   = self.request.query_params.get('employee')
        from_dt  = self.request.query_params.get('from')
        to_dt    = self.request.query_params.get('to')
        att_stat = self.request.query_params.get('status')
        dept_id  = self.request.query_params.get('department')

        if emp_id:
            qs = qs.filter(employee_id=emp_id)
        if from_dt:
            qs = qs.filter(date__gte=from_dt)
        if to_dt:
            qs = qs.filter(date__lte=to_dt)
        if att_stat:
            qs = qs.filter(status=att_stat)
        if dept_id:
            qs = qs.filter(employee__department_id=dept_id)

        # Non-managers see only their own records
        user = self.request.user
        if not user.is_manager_or_above:
            qs = qs.filter(employee=user)

        return qs

    # ── Check-in ──────────────────────────────────────────────────────────────

    @action(detail=False, methods=['post'])
    def check_in(self, request):
        employee = request.user
        today    = date.today()
        now_time = datetime.now().time()

        # Already checked in?
        existing = AttendanceRecord.objects.filter(employee=employee, date=today).first()
        if existing and existing.check_in_time:
            return Response({'error': 'Already checked in today.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CheckInSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data     = serializer.validated_data
        method   = data.get('method', 'manual')
        location = data.get('location', '')

        # Geo-fence validation
        if method == 'geo' and location:
            ok, msg = _validate_geo(employee.organization, location)
            if not ok:
                return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

        shift = _get_active_shift(employee, today)

        record, _ = AttendanceRecord.objects.get_or_create(
            employee=employee, date=today,
            defaults={'organization': employee.organization, 'shift': shift}
        )
        record.check_in_time     = now_time
        record.check_in_method   = method
        record.check_in_location = location
        record.check_in_device   = data.get('device', '')
        record.notes             = data.get('notes', '')
        record.status            = 'present'
        record.save()

        # Async notification
        try:
            from apps.notifications.tasks import send_notification
            send_notification.delay(
                recipient_id=employee.id,
                title='Check-in recorded',
                message=f'You checked in at {now_time.strftime("%H:%M")}.',
                notif_type='check_in',
                reference_id=record.id,
            )
        except Exception:
            pass

        return Response(AttendanceRecordSerializer(record).data, status=status.HTTP_200_OK)

    # ── Check-out ─────────────────────────────────────────────────────────────

    @action(detail=False, methods=['post'])
    def check_out(self, request):
        employee = request.user
        today    = date.today()
        now_time = datetime.now().time()

        record = AttendanceRecord.objects.filter(employee=employee, date=today).first()
        if not record or not record.check_in_time:
            return Response({'error': 'No check-in found for today.'}, status=status.HTTP_400_BAD_REQUEST)
        if record.check_out_time:
            return Response({'error': 'Already checked out today.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CheckOutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        record.check_out_time     = now_time
        record.check_out_method   = data.get('method', 'manual')
        record.check_out_location = data.get('location', '')
        record.check_out_device   = data.get('device', '')
        if data.get('notes'):
            record.notes = data['notes']
        record.save()  # triggers auto-computation

        try:
            from apps.notifications.tasks import send_notification
            send_notification.delay(
                recipient_id=employee.id,
                title='Check-out recorded',
                message=f'You checked out at {now_time.strftime("%H:%M")}. Hours: {record.working_hours}.',
                notif_type='check_out',
                reference_id=record.id,
            )
        except Exception:
            pass

        return Response(AttendanceRecordSerializer(record).data, status=status.HTTP_200_OK)

    # ── Today's summary ───────────────────────────────────────────────────────

    @action(detail=False, methods=['get'])
    def today(self, request):
        """All employee attendance for today (manager view)."""
        records = self.get_queryset().filter(date=date.today())
        return Response(AttendanceRecordSerializer(records, many=True).data)

    @action(detail=False, methods=['get'])
    def my_today(self, request):
        """Current user's attendance for today."""
        record = AttendanceRecord.objects.filter(employee=request.user, date=date.today()).first()
        if not record:
            return Response({'status': 'not_marked', 'date': str(date.today())})
        return Response(AttendanceRecordSerializer(record).data)

    # ── Summary ───────────────────────────────────────────────────────────────

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Attendance summary for an employee over a date range."""
        emp_id    = request.query_params.get('employee', request.user.id)
        from_date = request.query_params.get('from', str(date.today().replace(day=1)))
        to_date   = request.query_params.get('to',   str(date.today()))
        records   = AttendanceRecord.objects.filter(
            employee_id=emp_id,
            organization=_org(request),
            date__range=[from_date, to_date]
        )
        summary = {s: records.filter(status=s).count() for s, _ in AttendanceRecord.STATUS_CHOICES}
        summary['total'] = records.count()
        from django.db.models import Sum, Avg
        agg = records.aggregate(
            total_hours=Sum('working_hours'),
            total_overtime=Sum('overtime_hours'),
            avg_late_minutes=Avg('late_minutes'),
        )
        summary.update(agg)
        return Response(summary)

    # ── Bulk mark ─────────────────────────────────────────────────────────────

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsManagerOrAbove])
    def bulk_mark(self, request):
        """Manually mark attendance for multiple employees (admin/HR use)."""
        serializer = BulkAttendanceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        att_date = serializer.validated_data['date']
        records  = serializer.validated_data['records']
        org      = _org(request)
        created = updated = 0

        for rec in records:
            emp_id     = rec.get('employee')
            att_status = rec.get('status', 'present')
            obj, is_new = AttendanceRecord.objects.update_or_create(
                employee_id=emp_id, date=att_date,
                defaults={
                    'organization':    org,
                    'status':          att_status,
                    'check_in_time':   rec.get('check_in'),
                    'check_out_time':  rec.get('check_out'),
                    'notes':           rec.get('notes', ''),
                    'marked_by':       request.user,
                }
            )
            if is_new:
                created += 1
            else:
                updated += 1

        return Response({'created': created, 'updated': updated})


class AttendanceRegularizationViewSet(viewsets.ModelViewSet):
    serializer_class   = AttendanceRegularizationSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManagerAbove]
    queryset           = AttendanceRegularization.objects.all()

    def get_queryset(self):
        user = self.request.user
        org  = _org(user)
        qs   = AttendanceRegularization.objects.filter(
            employee__organization=org
        ).select_related('employee', 'attendance_record', 'reviewed_by') if org else AttendanceRegularization.objects.none()

        if not user.is_manager_or_above:
            qs = qs.filter(employee=user)

        stat = self.request.query_params.get('status')
        if stat:
            qs = qs.filter(status=stat)
        return qs

    def perform_create(self, serializer):
        serializer.save(employee=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsManagerOrAbove])
    def approve(self, request, pk=None):
        reg = self.get_object()
        if reg.status != 'pending':
            return Response({'error': 'Only pending requests can be approved.'}, status=400)
        reg.status      = 'approved'
        reg.reviewed_by = request.user
        reg.reviewed_at = timezone.now()
        reg.save()
        # Apply correction to attendance record
        record = reg.attendance_record
        if reg.requested_check_in:
            record.check_in_time = reg.requested_check_in
        if reg.requested_check_out:
            record.check_out_time = reg.requested_check_out
        record.is_regularized = True
        record.save()
        return Response(AttendanceRegularizationSerializer(reg).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsManagerOrAbove])
    def reject(self, request, pk=None):
        reg = self.get_object()
        if reg.status != 'pending':
            return Response({'error': 'Only pending requests can be rejected.'}, status=400)
        reg.status           = 'rejected'
        reg.reviewed_by      = request.user
        reg.reviewed_at      = timezone.now()
        reg.rejection_reason = request.data.get('reason', '')
        reg.save()
        return Response(AttendanceRegularizationSerializer(reg).data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        regs = self.get_queryset().filter(status='pending')
        return Response(AttendanceRegularizationSerializer(regs, many=True).data)
