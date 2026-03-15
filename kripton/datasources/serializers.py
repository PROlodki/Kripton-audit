from rest_framework import serializers
from .models import DataSource


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = (
            'id', 'user', 'name', 'type', 'connection_data', 'created_at',
            'last_load_status', 'last_load_at', 'last_load_error', 'last_load_rows',
        )
        read_only_fields = (
            'user', 'created_at',
            'last_load_status', 'last_load_at', 'last_load_error', 'last_load_rows',
        )
