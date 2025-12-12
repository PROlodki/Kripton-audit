from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework import generics, permissions
from .models import DataSource
from .serializers import DataSourceSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from kripton.datasources.services.preview import preview_table

class DataSourceListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DataSourceSerializer

    def get_queryset(self):
        return DataSource.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def post_queryset(self, data):
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PreviewView(APIView):
    permission_classes = (IsAuthenticated)

    def get(self, request, pk):
        datasource = DataSource.objects.get(pk=pk, user=request.user)
        table = f"datasource_{pk}"

        rows = preview_table(table)
        return Response({"rows": rows})

