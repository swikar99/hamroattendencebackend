from django.contrib import admin
from .models import ReportJob


@admin.register(ReportJob)
class ReportJobAdmin(admin.ModelAdmin):
    list_display  = ['id', 'report_type', 'format', 'status', 'requested_by',
                     'organization', 'created_at', 'completed_at']
    list_filter   = ['report_type', 'format', 'status', 'organization']
    search_fields = ['requested_by__email', 'organization__name']
    readonly_fields = ['created_at', 'completed_at', 'error', 'file_path']
