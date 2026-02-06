from django.contrib import admin
from kripton.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'user', 'action_type_display', 'resource_type', 'resource_id', 'ip_address_short')
    list_filter = ('action_type', 'resource_type', 'timestamp')
    search_fields = ('user__email', 'resource_type', 'resource_id', 'ip_address', 'user_agent')
    readonly_fields = ('user', 'action_type', 'resource_type', 'resource_id', 'details', 'ip_address', 'user_agent', 'timestamp')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)

    def action_type_display(self, obj):
        return obj.get_action_type_display()
    action_type_display.short_description = 'Действие'

    def ip_address_short(self, obj):
        return (obj.ip_address or '—')[:20]
    ip_address_short.short_description = 'IP'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
