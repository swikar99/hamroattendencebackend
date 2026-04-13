from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import CustomUser


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Embed role, org_id, and full name inside the JWT payload."""
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email']     = user.email
        token['role']      = user.role
        token['org_id']    = user.organization_id
        token['full_name'] = user.get_full_name()
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        # Track last login IP
        request = self.context.get('request')
        if request:
            ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
            if ip:
                user.last_login_ip = ip.split(',')[0].strip()
                user.save(update_fields=['last_login_ip'])
        data['user'] = {
            'id':           user.id,
            'email':        user.email,
            'full_name':    user.get_full_name(),
            'role':         user.role,
            'org_id':       user.organization_id,
            'org_name':     user.organization.name if user.organization else None,
            'profile_photo': user.profile_photo.url if user.profile_photo else None,
        }
        return data


class UserSerializer(serializers.ModelSerializer):
    full_name    = serializers.SerializerMethodField()
    org_name     = serializers.CharField(source='organization.name', read_only=True)
    dept_name    = serializers.CharField(source='department.name', read_only=True)
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'phone_number', 'profile_photo', 'date_of_birth',
            'gender', 'address', 'joining_date', 'employee_id',
            'organization', 'org_name', 'department', 'dept_name',
            'manager', 'manager_name', 'is_active',
        ]
        read_only_fields = ['id', 'employee_id']

    @extend_schema_field(OpenApiTypes.STR)
    def get_full_name(self, obj):
        return obj.get_full_name()

    @extend_schema_field(OpenApiTypes.STR)
    def get_manager_name(self, obj):
        return obj.manager.get_full_name() if obj.manager else None


class RegisterSerializer(serializers.ModelSerializer):
    password         = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model  = CustomUser
        fields = ['email', 'first_name', 'last_name', 'password', 'confirm_password', 'role', 'phone_number']

    def validate(self, data):
        if data['password'] != data.pop('confirm_password'):
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        from apps.organizations.models import Organization
        org = Organization.get_by_email(data['email'])
        if not org:
            raise serializers.ValidationError({
                'email': 'No organization registered with this email domain.'
            })
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        return CustomUser.objects.create_user(password=password, **validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Incorrect current password.')
        return value
