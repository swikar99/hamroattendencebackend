"""
URL configuration for attendanceSystem project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── New multi-app APIs ──────────────────────────────────────────────────
    path('api/', include('apps.accounts.urls')),
    path('api/', include('apps.organizations.urls')),
    path('api/', include('apps.shifts.urls')),
    path('api/', include('apps.attendance.urls')),
    path('api/', include('apps.leaves.urls')),
    path('api/', include('apps.reports.urls')),
    path('api/', include('apps.notifications.urls')),

    # ── OpenAPI / Swagger ───────────────────────────────────────────────────
    path('api/schema/', SpectacularAPIView.as_view(),                         name='schema'),
    path('api/docs/',   SpectacularSwaggerView.as_view(url_name='schema'),    name='swagger-ui'),
    path('api/redoc/',  SpectacularRedocView.as_view(url_name='schema'),      name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,  document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
