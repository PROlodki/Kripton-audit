from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Сериализатор лога аудита."""
    user_email = serializers.CharField(source='user.email', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = (
            'id', 'user', 'user_email', 'action_type', 'action_type_display',
            'resource_type', 'resource_id', 'details',
            'ip_address', 'user_agent', 'timestamp',
        )
        read_only_fields = fields
