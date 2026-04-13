from rest_framework import serializers
from .models import Shift, ShiftAssignment, Roster, Holiday


class ShiftSerializer(serializers.ModelSerializer):
    org_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model  = Shift
        fields = ['id', 'organization', 'org_name', 'name', 'type', 'start_time', 'end_time',
                  'grace_period_minutes', 'break_minutes', 'working_days',
                  'is_night_shift', 'total_hours', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class ShiftAssignmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    shift_name    = serializers.CharField(source='shift.name', read_only=True)

    class Meta:
        model  = ShiftAssignment
        fields = ['id', 'employee', 'employee_name', 'shift', 'shift_name',
                  'effective_from', 'effective_to', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_at', 'created_by']

    def get_employee_name(self, obj):
        return obj.employee.get_full_name()

    def validate(self, data):
        if data.get('effective_to') and data['effective_to'] < data['effective_from']:
            raise serializers.ValidationError('effective_to must be after effective_from.')
        return data


class RosterSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    shift_name    = serializers.CharField(source='shift.name', read_only=True)

    class Meta:
        model  = Roster
        fields = ['id', 'organization', 'employee', 'employee_name', 'date',
                  'shift', 'shift_name', 'notes', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_at', 'created_by']

    def get_employee_name(self, obj):
        return obj.employee.get_full_name()


class HolidaySerializer(serializers.ModelSerializer):
    org_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model  = Holiday
        fields = ['id', 'organization', 'org_name', 'name', 'date', 'type', 'is_paid', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']
