from rest_framework import serializers
from .models import AttendanceRecord, AttendanceRegularization


class AttendanceRecordSerializer(serializers.ModelSerializer):
    employee_name  = serializers.SerializerMethodField()
    shift_name     = serializers.CharField(source='shift.name', read_only=True)
    marked_by_name = serializers.SerializerMethodField()

    class Meta:
        model  = AttendanceRecord
        fields = [
            'id', 'employee', 'employee_name', 'organization', 'date', 'shift', 'shift_name',
            'check_in_time', 'check_in_method', 'check_in_location', 'check_in_device',
            'check_out_time', 'check_out_method', 'check_out_location', 'check_out_device',
            'status', 'working_hours', 'overtime_hours', 'is_late', 'late_minutes', 'is_half_day',
            'notes', 'marked_by', 'marked_by_name', 'is_regularized',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'working_hours', 'overtime_hours', 'is_late', 'late_minutes',
                            'is_half_day', 'is_regularized', 'created_at', 'updated_at']

    def get_employee_name(self, obj):
        return obj.employee.get_full_name()

    def get_marked_by_name(self, obj):
        return obj.marked_by.get_full_name() if obj.marked_by else None


class CheckInSerializer(serializers.Serializer):
    method   = serializers.ChoiceField(choices=AttendanceRecord.METHOD_CHOICES, default='manual')
    location = serializers.CharField(max_length=100, required=False, allow_blank=True)
    device   = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes    = serializers.CharField(required=False, allow_blank=True)


class CheckOutSerializer(serializers.Serializer):
    method   = serializers.ChoiceField(choices=AttendanceRecord.METHOD_CHOICES, default='manual')
    location = serializers.CharField(max_length=100, required=False, allow_blank=True)
    device   = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes    = serializers.CharField(required=False, allow_blank=True)


class BulkAttendanceSerializer(serializers.Serializer):
    """Mark attendance for multiple employees at once (manual/admin use)."""
    date    = serializers.DateField()
    records = serializers.ListField(child=serializers.DictField())


class AttendanceRegularizationSerializer(serializers.ModelSerializer):
    employee_name   = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    att_date        = serializers.DateField(source='attendance_record.date', read_only=True)

    class Meta:
        model  = AttendanceRegularization
        fields = [
            'id', 'employee', 'employee_name', 'attendance_record', 'att_date',
            'requested_check_in', 'requested_check_out', 'reason',
            'status', 'reviewed_by', 'reviewed_by_name', 'reviewed_at',
            'rejection_reason', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'created_at', 'updated_at']

    def get_employee_name(self, obj):
        return obj.employee.get_full_name()

    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.get_full_name() if obj.reviewed_by else None
