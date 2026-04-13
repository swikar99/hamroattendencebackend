from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import ReportJob


class ReportJobSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(
        source='requested_by.get_full_name', read_only=True
    )
    file_url = serializers.SerializerMethodField()

    class Meta:
        model  = ReportJob
        fields = ['id', 'report_type', 'format', 'status', 'parameters',
                  'requested_by_name', 'file_url', 'error', 'created_at', 'completed_at']
        read_only_fields = ['id', 'status', 'error', 'created_at', 'completed_at',
                            'requested_by_name', 'file_url']

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_file_url(self, obj):
        if obj.file_path:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.file_path.url) if request else obj.file_path.url
        return None
