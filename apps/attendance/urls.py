from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AttendanceRecordViewSet, AttendanceRegularizationViewSet

router = DefaultRouter()
router.register(r'attendance',           AttendanceRecordViewSet,        basename='attendance')
router.register(r'regularizations',      AttendanceRegularizationViewSet, basename='regularization')

urlpatterns = [path('', include(router.urls))]
