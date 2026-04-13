from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView
from .views import CustomTokenObtainPairView, UserViewSet, register_view

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/',    CustomTokenObtainPairView.as_view(), name='token_obtain'),
    path('auth/refresh/',  TokenRefreshView.as_view(),          name='token_refresh'),
    path('auth/logout/',   TokenBlacklistView.as_view(),        name='token_blacklist'),
    path('auth/register/', register_view,                       name='register'),
]
