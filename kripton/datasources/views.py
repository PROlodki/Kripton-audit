from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import generics, permissions
from .models import DataSource
from .serializers import DataSourceSerializer

class DataSourceListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DataSourceSerializer

    def get_queryset(self):
        return DataSource.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PreviewView(APIView):
    permission_classes = (IsAuthenticated)

    def get(self, request, pk):
        datasource = DataSource.objects.get(pk=pk, user=request.user)
        table = f"datasource_{pk}"

        rows = preview_table(table)
        return Response({"rows": rows})
