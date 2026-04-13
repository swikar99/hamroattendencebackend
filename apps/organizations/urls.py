from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrganizationViewSet, DepartmentViewSet, AcademicYearViewSet,
    ClassViewSet, SectionViewSet, SubjectViewSet, StudentViewSet
)

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet,  basename='organization')
router.register(r'departments',   DepartmentViewSet,    basename='department')
router.register(r'academic-years',AcademicYearViewSet,  basename='academic-year')
router.register(r'classes',       ClassViewSet,         basename='class')
router.register(r'sections',      SectionViewSet,       basename='section')
router.register(r'subjects',      SubjectViewSet,       basename='subject')
router.register(r'students',      StudentViewSet,       basename='student')

urlpatterns = [path('', include(router.urls))]
