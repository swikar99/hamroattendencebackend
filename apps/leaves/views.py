from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import date
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import LeaveType, LeaveBalance, LeaveRequest, LeaveApproval
from .serializers import (
    LeaveTypeSerializer, LeaveBalanceSerializer,
    LeaveRequestSerializer, LeaveApprovalSerializer
)
from apps.accounts.permissions import IsHROrAbove, IsManagerOrAbove, IsSameOrg, IsOwnerOrManagerAbove


def _org(request):
    return request.user.organization


@extend_schema(tags=['Leaves'])
class LeaveTypeViewSet(viewsets.ModelViewSet):
    serializer_class   = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]
    queryset           = LeaveType.objects.all()

    def get_queryset(self):
        org = _org(self.request)
        return LeaveType.objects.filter(organization=org, is_active=True) if org else LeaveType.objects.none()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsHROrAbove()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(organization=_org(self.request))


@extend_schema(tags=['Leaves'])
class LeaveBalanceViewSet(viewsets.ModelViewSet):
    serializer_class   = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]
    queryset           = LeaveBalance.objects.all()

    def get_queryset(self):
        user = self.request.user
        org  = _org(user)
        qs   = LeaveBalance.objects.filter(
            employee__organization=org
        ).select_related('employee', 'leave_type') if org else LeaveBalance.objects.none()

        if not user.is_manager_or_above:
            qs = qs.filter(employee=user)

        emp_id = self.request.query_params.get('employee')
        year   = self.request.query_params.get('year', date.today().year)
        if emp_id:
            qs = qs.filter(employee_id=emp_id)
        if year:
            qs = qs.filter(year=year)
        return qs

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsHROrAbove()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def my_balance(self, request):
        """Return the logged-in user's leave balances for the current year."""
        year = request.query_params.get('year', date.today().year)
        balances = LeaveBalance.objects.filter(employee=request.user, year=year).select_related('leave_type')
        return Response(LeaveBalanceSerializer(balances, many=True).data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsHROrAbove])
    def allocate_bulk(self, request):
        """Bulk-allocate leave for all employees in an org for a year."""
        year = request.data.get('year', date.today().year)
        org  = _org(request)
        leave_types = LeaveType.objects.filter(organization=org, is_active=True)
        from apps.accounts.models import CustomUser
        employees = CustomUser.objects.filter(organization=org, is_active=True).exclude(role='student')
        created = 0
        for emp in employees:
            for lt in leave_types:
                _, is_new = LeaveBalance.objects.get_or_create(
                    employee=emp, leave_type=lt, year=year,
                    defaults={'allocated': lt.max_days_per_year}
                )
                if is_new:
                    created += 1
        return Response({'allocated': created, 'year': year})


@extend_schema(tags=['Leaves'])
class LeaveRequestViewSet(viewsets.ModelViewSet):
    serializer_class   = LeaveRequestSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManagerAbove]
    queryset           = LeaveRequest.objects.all()
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['employee__first_name', 'employee__last_name', 'leave_type__name']
    ordering_fields    = ['start_date', 'created_at']

    def get_queryset(self):
        user = self.request.user
        org  = _org(user)
        qs   = LeaveRequest.objects.filter(
            employee__organization=org
        ).select_related('employee', 'leave_type', 'final_approved_by').prefetch_related('approvals') if org else LeaveRequest.objects.none()

        if not user.is_manager_or_above:
            qs = qs.filter(employee=user)

        stat      = self.request.query_params.get('status')
        emp_id    = self.request.query_params.get('employee')
        from_date = self.request.query_params.get('from')
        to_date   = self.request.query_params.get('to')

        if stat:
            qs = qs.filter(status=stat)
        if emp_id:
            qs = qs.filter(employee_id=emp_id)
        if from_date:
            qs = qs.filter(start_date__gte=from_date)
        if to_date:
            qs = qs.filter(end_date__lte=to_date)
        return qs

    def perform_create(self, serializer):
        employee = self.request.user
        # Auto-assign manager from employee's profile
        manager    = employee.manager
        hr_manager = None
        from apps.accounts.models import CustomUser
        hr_qs = CustomUser.objects.filter(organization=employee.organization, role='hr_manager')
        if hr_qs.exists():
            hr_manager = hr_qs.first()
        serializer.save(employee=employee, manager=manager, hr_manager=hr_manager)

    def _deduct_balance(self, leave_request):
        today_year = date.today().year
        balance, _ = LeaveBalance.objects.get_or_create(
            employee=leave_request.employee,
            leave_type=leave_request.leave_type,
            year=today_year,
            defaults={'allocated': leave_request.leave_type.max_days_per_year}
        )
        balance.used += leave_request.total_days
        balance.save()

    def _restore_balance(self, leave_request):
        try:
            balance = LeaveBalance.objects.get(
                employee=leave_request.employee,
                leave_type=leave_request.leave_type,
                year=date.today().year
            )
            balance.used = max(balance.used - leave_request.total_days, 0)
            balance.save()
        except LeaveBalance.DoesNotExist:
            pass

    # ── Approve ───────────────────────────────────────────────────────────────

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsManagerOrAbove])
    def approve(self, request, pk=None):
        leave    = self.get_object()
        approver = request.user
        comments = request.data.get('comments', '')

        if leave.status in ('approved', 'rejected', 'cancelled'):
            return Response({'error': f'Cannot approve a {leave.status} request.'}, status=400)

        # Determine approval level
        if approver.role == 'manager' and leave.status == 'pending':
            level = 1
            if leave.hr_manager:
                leave.status = 'manager_approved'
            else:
                leave.status = 'approved'
                leave.final_approved_by = approver
                self._deduct_balance(leave)
        elif approver.role in ('hr_manager', 'org_admin', 'superadmin'):
            level = 2
            leave.status = 'approved'
            leave.final_approved_by = approver
            self._deduct_balance(leave)
        else:
            return Response({'error': 'You do not have permission to approve at this level.'}, status=403)

        leave.save()
        LeaveApproval.objects.create(
            leave_request=leave, approver=approver, level=level,
            action='approved', comments=comments
        )
        # Notify employee
        try:
            from apps.notifications.tasks import send_notification
            send_notification.delay(
                recipient_id=leave.employee_id,
                title='Leave Request Approved',
                message=f'Your {leave.leave_type.name} request ({leave.start_date}→{leave.end_date}) was approved by {approver.get_full_name()}.',
                notif_type='leave_approved',
                reference_id=leave.id,
            )
        except Exception:
            pass
        return Response(LeaveRequestSerializer(leave).data)

    # ── Reject ────────────────────────────────────────────────────────────────

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsManagerOrAbove])
    def reject(self, request, pk=None):
        leave    = self.get_object()
        approver = request.user
        reason   = request.data.get('reason', '')

        if leave.status in ('approved', 'rejected', 'cancelled'):
            return Response({'error': f'Cannot reject a {leave.status} request.'}, status=400)

        level = 1 if approver.role == 'manager' else 2
        leave.status           = 'rejected'
        leave.rejection_reason = reason
        leave.save()

        LeaveApproval.objects.create(
            leave_request=leave, approver=approver, level=level,
            action='rejected', comments=reason
        )
        try:
            from apps.notifications.tasks import send_notification
            send_notification.delay(
                recipient_id=leave.employee_id,
                title='Leave Request Rejected',
                message=f'Your {leave.leave_type.name} request was rejected. Reason: {reason}',
                notif_type='leave_rejected',
                reference_id=leave.id,
            )
        except Exception:
            pass
        return Response(LeaveRequestSerializer(leave).data)

    # ── Cancel ────────────────────────────────────────────────────────────────

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        leave = self.get_object()
        if leave.employee != request.user and not request.user.is_manager_or_above:
            return Response({'error': 'Not authorized.'}, status=403)
        if leave.status == 'approved':
            self._restore_balance(leave)
        if leave.status in ('rejected', 'cancelled'):
            return Response({'error': f'Cannot cancel a {leave.status} request.'}, status=400)
        leave.status = 'cancelled'
        leave.save()
        return Response(LeaveRequestSerializer(leave).data)

    # ── Pending queue ─────────────────────────────────────────────────────────

    @action(detail=False, methods=['get'])
    def pending(self, request):
        leaves = self.get_queryset().filter(status='pending')
        return Response(LeaveRequestSerializer(leaves, many=True).data)

    # ── Calendar ──────────────────────────────────────────────────────────────

    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """Return approved leaves in a date range for calendar display."""
        from_date = request.query_params.get('from', str(date.today().replace(day=1)))
        to_date   = request.query_params.get('to',   str(date.today()))
        leaves = self.get_queryset().filter(
            status='approved',
            start_date__lte=to_date,
            end_date__gte=from_date,
        )
        data = []
        for leave in leaves:
            data.append({
                'id':          leave.id,
                'employee':    leave.employee.get_full_name(),
                'leave_type':  leave.leave_type.name,
                'color':       leave.leave_type.color,
                'start':       str(leave.start_date),
                'end':         str(leave.end_date),
                'total_days':  str(leave.total_days),
            })
        return Response(data)
