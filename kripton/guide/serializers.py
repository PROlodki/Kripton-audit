from rest_framework import serializers
from .models import Department

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:

        model = Department
        fields = [
            'name',
            'parent',
            'head_of_department',
            'is_active',
            'description'
        ]

    def validate(self, attrs):

        head_of_department = attrs.get('head_of_department')
        parent = attrs.get('parent')

        if parent and head_of_department and head_of_department.department != parent:
            raise serializers.ValidationError(
                'Начальник не должен принадлежать родительскому подразделению'
           )

        return attrs

class DepartmentListSerializer(serializers.ModelSerializer):
    # TODO Допилить до ума (чтобы был "список" подразделений)
    class Meta:
        model = Department
        fields = ('id', 'name', 'parent')
