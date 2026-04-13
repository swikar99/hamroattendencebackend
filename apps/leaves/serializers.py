from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import LeaveType, LeaveBalance, LeaveRequest, LeaveApproval


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LeaveType
        fields = ['id', 'organization', 'name', 'code', 'description', 'max_days_per_year',
                  'is_paid', 'requires_approval', 'can_carry_forward', 'max_carry_forward_days',
                  'applicable_gender', 'min_days', 'requires_document', 'notice_days_required',
                  'color', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    employee_name   = serializers.SerializerMethodField()
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)
    remaining       = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)
    total_available = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model  = LeaveBalance
        fields = ['id', 'employee', 'employee_name', 'leave_type', 'leave_type_name',
                  'leave_type_code', 'year', 'allocated', 'used', 'carried_forward',
                  'lapsed', 'remaining', 'total_available', 'updated_at']
        read_only_fields = ['id', 'updated_at']

    @extend_schema_field(serializers.CharField())
    def get_employee_name(self, obj):
        return obj.employee.get_full_name()


class LeaveApprovalSerializer(serializers.ModelSerializer):
    approver_name = serializers.SerializerMethodField()

    class Meta:
        model  = LeaveApproval
        fields = ['id', 'leave_request', 'approver', 'approver_name', 'level', 'action', 'comments', 'acted_at']
        read_only_fields = ['id', 'acted_at']

    @extend_schema_field(serializers.CharField())
    def get_approver_name(self, obj):
        return obj.approver.get_full_name()


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name     = serializers.SerializerMethodField()
    leave_type_name   = serializers.CharField(source='leave_type.name', read_only=True)
    leave_type_code   = serializers.CharField(source='leave_type.code', read_only=True)
    duration_label    = serializers.CharField(read_only=True)
    approvals         = LeaveApprovalSerializer(many=True, read_only=True)
    approved_by_name  = serializers.SerializerMethodField()

    class Meta:
        model  = LeaveRequest
        fields = ['id', 'employee', 'employee_name', 'leave_type', 'leave_type_name',
                  'leave_type_code', 'start_date', 'end_date', 'total_days', 'is_half_day',
                  'half_day_period', 'reason', 'attachment', 'status', 'duration_label',
                  'manager', 'hr_manager', 'final_approved_by', 'approved_by_name',
                  'rejection_reason', 'is_emergency', 'approvals', 'created_at', 'updated_at']
        read_only_fields = ['id', 'total_days', 'status', 'final_approved_by',
                            'rejection_reason', 'created_at', 'updated_at']

    @extend_schema_field(serializers.CharField())
    def get_employee_name(self, obj):
        return obj.employee.get_full_name()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_approved_by_name(self, obj):
        return obj.final_approved_by.get_full_name() if obj.final_approved_by else None

    def validate(self, data):
        start = data.get('start_date') or (self.instance and self.instance.start_date)
        end   = data.get('end_date')   or (self.instance and self.instance.end_date)
        if end and start and end < start:
            raise serializers.ValidationError('end_date must be after start_date.')
        return data

    def create(self, validated_data):
        # Auto-compute total_days
        instance = LeaveRequest(**validated_data)
        instance.total_days = instance.calculate_days()
        instance.save()
        return instance
