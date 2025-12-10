from rest_framework import serializers
from .models import DataSource

class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = "__all__"
        read_only_fields = ('user', 'created_at')
