from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import PersonalData, Department, ReportType, Report, ReportRequest

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя (authpage.User: нет first_name/last_name)."""
    class Meta:
        model = User
        fields = ('id', 'username', 'email')


class DepartmentSerializer(serializers.ModelSerializer):
    head_info = UserSerializer(source='head_of_department', read_only=True)
    
    class Meta:
        model = Department
        fields = (
            'id', 'name', 'code', 'description',
            'head_of_department', 'head_info', 'created_at',
            'parent', 'is_active'
        )


class ReportTypeSerializer(serializers.ModelSerializer):
    stakeholders_info = UserSerializer(source='stakeholders', many=True, read_only=True)
    
    class Meta:
        model = ReportType
        fields = ('id', 'name', 'code', 'description', 'template', 
                 'stakeholders', 'stakeholders_info', 'is_active', 'created_at')


class ReportListSerializer(serializers.ModelSerializer):
    """Краткий сериализатор отчёта для списков."""
    created_by_info = UserSerializer(source='created_by', read_only=True)
    report_type_name = serializers.CharField(source='report_type.name', read_only=True)
    
    class Meta:
        model = Report
        fields = ('id', 'title', 'report_type', 'report_type_name', 'created_by', 'created_by_info', 'created_at', 'submitted_at', 'approved_at')


class ReportSerializer(serializers.ModelSerializer):
    """Полный сериализатор отчёта."""
    created_by_info = UserSerializer(source='created_by', read_only=True)
    report_type_info = ReportTypeSerializer(source='report_type', read_only=True)
    approved_by_info = UserSerializer(source='approved_by', read_only=True)
    
    class Meta:
        model = Report
        fields = (
            'id', 'title', 'report_type', 'report_type_info', 'description',
            'clickhouse_table', 'clickhouse_query', 'data', 'file',
            'created_by', 'created_by_info', 'created_at',
            'submitted_at', 'approved_at', 'approved_by', 'approved_by_info',
        )


class ReportRequestSerializer(serializers.ModelSerializer):
    requester_info = UserSerializer(source='requester', read_only=True)
    department_info = DepartmentSerializer(source='department', read_only=True)
    report_type_info = ReportTypeSerializer(source='report_type', read_only=True)
    approved_by_info = UserSerializer(source='approved_by', read_only=True)
    report_info = ReportSerializer(source='report', read_only=True)
    
    can_approve = serializers.SerializerMethodField()
    can_view = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = ReportRequest
        fields = (
            'id', 'requester', 'requester_info', 'department', 'department_info',
            'report_type', 'report_type_info', 'title', 'description', 'status',
            'status_display', 'rejection_reason', 'report', 'report_info',
            'approved_by', 'approved_by_info', 'created_at', 'updated_at',
            'approved_at', 'completed_at', 'priority', 'priority_display',
            'deadline', 'can_approve', 'can_view'
        )
        read_only_fields = (
            'status', 'rejection_reason', 'report', 'approved_by',
            'approved_at', 'completed_at', 'created_at', 'updated_at',
            'can_approve', 'can_view'
        )
    
    def get_can_approve(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.can_approve(request.user)
        return False
    
    def get_can_view(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.can_view(request.user)
        return False
    
    def validate(self, data):
        """Дополнительная валидация при создании"""
        request = self.context.get('request')
        
        if request and request.user:
            # Автоматически устанавливаем заявителя
            data['requester'] = request.user
            
            # Проверяем, может ли пользователь создавать запросы этого типа
            if 'report_type' in data:
                report_type = data['report_type']
                if not report_type.allowed_creators.filter(id=request.user.id).exists():
                    if not (request.user.is_staff or request.user.is_superuser):
                        raise serializers.ValidationError(
                            "Вы не можете создавать запросы этого типа отчета"
                        )
        
        return data


class ReportRequestActionSerializer(serializers.Serializer):
    """Для действий с запросом"""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        if data['action'] == 'reject' and not data.get('rejection_reason'):
            raise serializers.ValidationError(
                "При отклонении необходимо указать причину"
            )
        return data

class PersonalDataSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    work_experience = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    
    class Meta:
        model = PersonalData
        fields = [
            'id',
            'full_name',
            'last_name',
            'first_name',
            'middle_name',
            'position',
            'rank',
            'department',
            'department_name',
            'hire_date',
            'dismissal_date',
            'is_active',
            'work_experience',
            'additional_data',
            'created_at',
            'updated_at',
            'user'
        ]
        read_only_fields = ['created_at', 'updated_at', 'work_experience']
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_work_experience(self, obj):
        return obj.work_experience