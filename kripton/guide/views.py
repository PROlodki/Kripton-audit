from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .serializers import DepartmentSerializer
from .models import Department

class DepartmentCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]  # JWT токен проверяется здесь

    def post(self, request):
        serializer = DepartmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        queryset = Department.objects.filter(is_active=True)
        serializer = DepartmentSerializer(queryset, many=True)
        return Response(serializer.data)

    def patch(self, request, pk):
        department = get_object_or_404(Department, pk=pk)
        serializer = DepartmentSerializer(
            department, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        department = get_object_or_404(Department, pk=pk)
        department.is_active = False  # soft delete
        department.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)