from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from datetime import date

from .models import Shift, ShiftAssignment, Roster, Holiday
from .serializers import ShiftSerializer, ShiftAssignmentSerializer, RosterSerializer, HolidaySerializer
from apps.accounts.permissions import IsManagerOrAbove, IsHROrAbove, IsSameOrg


def _org(request):
    return request.user.organization


class ShiftViewSet(viewsets.ModelViewSet):
    serializer_class   = ShiftSerializer
    permission_classes = [IsAuthenticated, IsSameOrg]
    queryset           = Shift.objects.all()
    filter_backends    = [filters.SearchFilter]
    search_fields      = ['name', 'type']

    def get_queryset(self):
        org = _org(self.request)
        return Shift.objects.filter(organization=org, is_active=True) if org else Shift.objects.none()

    def perform_create(self, serializer):
        serializer.save(organization=_org(self.request))

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsHROrAbove()]
        return [IsAuthenticated()]


class ShiftAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class   = ShiftAssignmentSerializer
    permission_classes = [IsAuthenticated]
    queryset           = ShiftAssignment.objects.all()
    filter_backends    = [filters.OrderingFilter]
    ordering_fields    = ['effective_from']

    def get_queryset(self):
        org = _org(self.request)
        qs = ShiftAssignment.objects.filter(
            employee__organization=org
        ).select_related('employee', 'shift') if org else ShiftAssignment.objects.none()
        emp_id = self.request.query_params.get('employee')
        if emp_id:
            qs = qs.filter(employee_id=emp_id)
        return qs

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsManagerOrAbove()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get the current active shift for an employee."""
        emp_id = request.query_params.get('employee', request.user.id)
        today  = date.today()
        assignment = ShiftAssignment.objects.filter(
            employee_id=emp_id,
            effective_from__lte=today,
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=today)
        ).order_by('-effective_from').first()
        if not assignment:
            return Response({'detail': 'No active shift assignment found.'}, status=404)
        return Response(ShiftAssignmentSerializer(assignment).data)


class RosterViewSet(viewsets.ModelViewSet):
    serializer_class   = RosterSerializer
    permission_classes = [IsAuthenticated]
    queryset           = Roster.objects.all()
    filter_backends    = [filters.OrderingFilter]
    ordering_fields    = ['date']

    def get_queryset(self):
        org = _org(self.request)
        qs = Roster.objects.filter(organization=org).select_related('employee', 'shift') if org else Roster.objects.none()
        emp_id  = self.request.query_params.get('employee')
        from_dt = self.request.query_params.get('from')
        to_dt   = self.request.query_params.get('to')
        if emp_id:
            qs = qs.filter(employee_id=emp_id)
        if from_dt:
            qs = qs.filter(date__gte=from_dt)
        if to_dt:
            qs = qs.filter(date__lte=to_dt)
        return qs

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsManagerOrAbove()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(organization=_org(self.request), created_by=self.request.user)


class HolidayViewSet(viewsets.ModelViewSet):
    serializer_class   = HolidaySerializer
    permission_classes = [IsAuthenticated]
    queryset           = Holiday.objects.all()
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name']
    ordering_fields    = ['date']

    def get_queryset(self):
        org = _org(self.request)
        return Holiday.objects.filter(organization=org) if org else Holiday.objects.none()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsHROrAbove()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(organization=_org(self.request))

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        holidays = self.get_queryset().filter(date__gte=date.today()).order_by('date')[:10]
        return Response(HolidaySerializer(holidays, many=True).data)
