from rest_framework import serializers
from .models import Department

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = [
            'id',
            'name',
            'code',
            'parent',
            'head_of_department',
            'is_active',
            'description',
            'employees'
            'created_at',
        ]

    def validate(self, attrs):
        head_of_department = attrs.get('head_of_department')
        parent = attrs.get('parent')
        # Проверка только если у пользователя есть связь с отделом (например, через профиль)
        if parent and head_of_department and hasattr(head_of_department, 'department') and head_of_department.department != parent:
            raise serializers.ValidationError(
                'Начальник не должен принадлежать родительскому подразделению'
            )
        return attrs

class DepartmentListSerializer(serializers.ModelSerializer):
    # TODO Допилить до ума (чтобы был "список" подразделений)
    class Meta:
        model = Department
        fields = ('id', 'name', 'parent')
