from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ShiftViewSet, ShiftAssignmentViewSet, RosterViewSet, HolidayViewSet

router = DefaultRouter()
router.register(r'shifts',            ShiftViewSet,           basename='shift')
router.register(r'shift-assignments', ShiftAssignmentViewSet, basename='shift-assignment')
router.register(r'rosters',           RosterViewSet,          basename='roster')
router.register(r'holidays',          HolidayViewSet,         basename='holiday')

urlpatterns = [path('', include(router.urls))]
