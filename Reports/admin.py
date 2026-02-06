from django.contrib import admin
from .models import PersonalData, Department, ReportType, Report, ReportRequest


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'head_of_department', 'created_at')
    list_filter = ('created_at', 'is_active')
    search_fields = ('name', 'code', 'head_of_department__username')
    raw_id_fields = ('head_of_department', 'parent')


@admin.register(ReportType)
class ReportTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code')
    filter_horizontal = ('stakeholders', 'allowed_creators')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'report_type', 'created_by', 'created_at')
    list_filter = ('report_type', 'created_at')
    search_fields = ('title', 'created_by__username')
    raw_id_fields = ('created_by',)


@admin.register(ReportRequest)
class ReportRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'requester', 'department', 
                   'report_type', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority', 'department', 'report_type', 'created_at')
    search_fields = ('title', 'description', 'requester__username')
    readonly_fields = ('created_at', 'updated_at', 'approved_at', 'completed_at')
    raw_id_fields = ('requester', 'approved_by', 'report')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('requester', 'department', 'report_type', 
                      'title', 'description', 'priority', 'deadline')
        }),
        ('Статус', {
            'fields': ('status', 'rejection_reason', 'report')
        }),
        ('Утверждение', {
            'fields': ('approved_by', 'approved_at')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_selected', 'reject_selected']
    
    def approve_selected(self, request, queryset):
        """Действие для утверждения выбранных запросов"""
        count = 0
        for obj in queryset:
            if obj.can_approve(request.user):
                obj.approve(request.user)
                count += 1
        self.message_user(request, f"Утверждено {count} запросов")
    approve_selected.short_description = "Утвердить выбранные запросы"
    
    def reject_selected(self, request, queryset):
        """Действие для отклонения выбранных запросов"""
        count = 0
        for obj in queryset:
            if obj.can_approve(request.user):
                obj.approve(request.user, rejection_reason="Отклонено администратором")
                count += 1
        self.message_user(request, f"Отклонено {count} запросов")
    reject_selected.short_description = "Отклонить выбранные запросы"

@admin.register(PersonalData)
class PersonalDataAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'position', 'department', 'is_active', 'hire_date']
    list_filter = ['is_active', 'department', 'position']
    search_fields = ['last_name', 'first_name', 'middle_name', 'position']
    readonly_fields = ['created_at', 'updated_at', 'work_experience_display']
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'department', 'last_name', 'first_name', 'middle_name')
        }),
        ('Рабочая информация', {
            'fields': ('position', 'rank', 'hire_date', 'dismissal_date', 'is_active')
        }),
        ('Дополнительно', {
            'fields': ('additional_data',)
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'ФИО'
    get_full_name.admin_order_field = 'last_name'
    
    def work_experience_display(self, obj):
        return f"{obj.work_experience} лет"
    work_experience_display.short_description = 'Стаж работы'