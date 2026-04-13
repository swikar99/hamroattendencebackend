from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from .models import Organization, OrganizationSettings, Department, AcademicYear, Class, Section, Subject, Student
from .serializers import (
    OrganizationSerializer, OrganizationSettingsSerializer, DepartmentSerializer,
    AcademicYearSerializer, ClassSerializer, SectionSerializer, SubjectSerializer, StudentSerializer
)
from apps.accounts.permissions import IsOrgAdminOrAbove, IsHROrAbove, IsSameOrg


def _org(request):
    return request.user.organization


class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class   = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    queryset           = Organization.objects.all()
    filter_backends    = [filters.SearchFilter]
    search_fields      = ['name', 'email_domain', 'type']

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            return [IsAdminUser()]
        if self.action in ['update', 'partial_update']:
            return [IsAuthenticated(), IsOrgAdminOrAbove()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['get', 'put', 'patch'])
    def org_settings(self, request, pk=None):
        org = self.get_object()
        settings, _ = OrganizationSettings.objects.get_or_create(organization=org)
        if request.method == 'GET':
            return Response(OrganizationSettingsSerializer(settings).data)
        serializer = OrganizationSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class   = DepartmentSerializer
    permission_classes = [IsAuthenticated, IsSameOrg]
    queryset           = Department.objects.all()
    filter_backends    = [filters.SearchFilter]
    search_fields      = ['name']

    def get_queryset(self):
        org = _org(self.request)
        return Department.objects.filter(organization=org).select_related('manager') if org else Department.objects.none()

    def perform_create(self, serializer):
        serializer.save(organization=_org(self.request))


class AcademicYearViewSet(viewsets.ModelViewSet):
    serializer_class   = AcademicYearSerializer
    permission_classes = [IsAuthenticated]
    queryset           = AcademicYear.objects.all()

    def get_queryset(self):
        org = _org(self.request)
        return AcademicYear.objects.filter(organization=org) if org else AcademicYear.objects.none()

    def perform_create(self, serializer):
        serializer.save(organization=_org(self.request))


class ClassViewSet(viewsets.ModelViewSet):
    serializer_class   = ClassSerializer
    permission_classes = [IsAuthenticated]
    queryset           = Class.objects.all()
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name']
    ordering_fields    = ['order', 'name']

    def get_queryset(self):
        org = _org(self.request)
        return Class.objects.filter(organization=org) if org else Class.objects.none()

    def perform_create(self, serializer):
        serializer.save(organization=_org(self.request))


class SectionViewSet(viewsets.ModelViewSet):
    serializer_class   = SectionSerializer
    permission_classes = [IsAuthenticated]
    queryset           = Section.objects.all()

    def get_queryset(self):
        org = _org(self.request)
        return Section.objects.filter(grade__organization=org) if org else Section.objects.none()


class SubjectViewSet(viewsets.ModelViewSet):
    serializer_class   = SubjectSerializer
    permission_classes = [IsAuthenticated]
    queryset           = Subject.objects.all()
    filter_backends    = [filters.SearchFilter]
    search_fields      = ['name', 'code']

    def get_queryset(self):
        org = _org(self.request)
        return Subject.objects.filter(organization=org) if org else Subject.objects.none()

    def perform_create(self, serializer):
        serializer.save(organization=_org(self.request))


class StudentViewSet(viewsets.ModelViewSet):
    serializer_class   = StudentSerializer
    permission_classes = [IsAuthenticated]
    queryset           = Student.objects.all()
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['roll_number', 'user__first_name', 'user__last_name', 'parent_name']
    ordering_fields    = ['roll_number', 'admission_date']

    def get_queryset(self):
        org = _org(self.request)
        qs = Student.objects.filter(organization=org).select_related('user', 'section__grade') if org else Student.objects.none()
        section_id = self.request.query_params.get('section')
        class_id   = self.request.query_params.get('class')
        if section_id:
            qs = qs.filter(section_id=section_id)
        if class_id:
            qs = qs.filter(section__grade_id=class_id)
        return qs
