from django.contrib import admin
from .models import Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'head_of_department', 'created_at')
    list_filter = ('created_at', 'is_active')
    search_fields = ('name', 'code', 'head_of_department__username')
    raw_id_fields = ('head_of_department', 'parent')
