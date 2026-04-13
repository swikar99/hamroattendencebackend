from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Organization, OrganizationSettings, Department, AcademicYear, Class, Section, Subject, Student


class OrganizationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OrganizationSettings
        fields = '__all__'
        read_only_fields = ['organization']


class OrganizationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    settings     = OrganizationSettingsSerializer(read_only=True)

    class Meta:
        model  = Organization
        fields = ['id', 'name', 'type', 'type_display', 'email', 'email_domain',
                  'phone', 'address', 'logo', 'head_name', 'established',
                  'timezone', 'currency', 'is_active', 'created_at', 'settings']
        read_only_fields = ['id', 'created_at']


class DepartmentSerializer(serializers.ModelSerializer):
    org_name     = serializers.CharField(source='organization.name', read_only=True)
    manager_name = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model  = Department
        fields = ['id', 'organization', 'org_name', 'name', 'description',
                  'manager', 'manager_name', 'parent', 'member_count', 'created_at']
        read_only_fields = ['id', 'created_at']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_manager_name(self, obj):
        return obj.manager.get_full_name() if obj.manager else None

    @extend_schema_field(serializers.IntegerField())
    def get_member_count(self, obj):
        return obj.members.filter(is_active=True).count()


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AcademicYear
        fields = ['id', 'organization', 'name', 'start_date', 'end_date', 'is_current', 'created_at']
        read_only_fields = ['id', 'created_at']


class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Class
        fields = ['id', 'organization', 'academic_year', 'name', 'order', 'created_at']
        read_only_fields = ['id', 'created_at']


class SectionSerializer(serializers.ModelSerializer):
    grade_name    = serializers.CharField(source='grade.name', read_only=True)
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model  = Section
        fields = ['id', 'grade', 'grade_name', 'name', 'max_students', 'student_count', 'created_at']
        read_only_fields = ['id', 'created_at']


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Subject
        fields = ['id', 'organization', 'name', 'code', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class StudentSerializer(serializers.ModelSerializer):
    from apps.accounts.serializers import UserSerializer
    user         = UserSerializer(read_only=True)
    section_name = serializers.CharField(source='section.__str__', read_only=True)
    class_name   = serializers.CharField(source='section.grade.name', read_only=True)

    class Meta:
        model  = Student
        fields = ['id', 'user', 'roll_number', 'organization', 'section', 'section_name',
                  'class_name', 'date_of_birth', 'gender', 'blood_group', 'address',
                  'parent_name', 'parent_phone', 'parent_email', 'admission_date', 'status',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'roll_number', 'created_at', 'updated_at']
