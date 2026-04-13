from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display   = ['email', 'first_name', 'last_name', 'role', 'organization', 'department', 'is_active']
    list_filter    = ['role', 'organization', 'is_active', 'is_staff']
    search_fields  = ['email', 'first_name', 'last_name', 'employee_id']
    ordering       = ['email']
    fieldsets = (
        (None,                  {'fields': ('email', 'password')}),
        ('Personal Info',       {'fields': ('first_name', 'last_name', 'phone_number', 'profile_photo', 'date_of_birth', 'gender', 'address')}),
        ('Org & Role',          {'fields': ('organization', 'department', 'manager', 'role', 'joining_date', 'employee_id')}),
        ('Permissions',         {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates',               {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'role', 'organization')}),
    )
