from django.contrib import admin
from .models import Organization, OrganizationSettings, Department, AcademicYear, Class, Section, Subject, Student


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display  = ['name', 'type', 'email_domain', 'head_name', 'is_active']
    list_filter   = ['type', 'is_active']
    search_fields = ['name', 'email_domain']


@admin.register(OrganizationSettings)
class OrganizationSettingsAdmin(admin.ModelAdmin):
    list_display = ['organization', 'default_work_start', 'default_work_end', 'grace_period_minutes']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display  = ['name', 'organization', 'manager']
    list_filter   = ['organization']
    search_fields = ['name']


admin.site.register(AcademicYear)
admin.site.register(Class)
admin.site.register(Section)
admin.site.register(Subject)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display  = ['roll_number', 'user', 'organization', 'section', 'status']
    list_filter   = ['organization', 'status']
    search_fields = ['roll_number', 'user__first_name', 'user__last_name']
    readonly_fields = ['roll_number']
