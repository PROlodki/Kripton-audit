from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import DataSource
from .serializers import DataSourceSerializer
from .services import (
    DataLoaderService,
    DataValidatorService,
    DataPreviewService,
)


class DataSourceViewSet(viewsets.ModelViewSet):
    """Список и CRUD источников данных + тест подключения, загрузка, статус, предпросмотр."""
    permission_classes = [IsAuthenticated]
    serializer_class = DataSourceSerializer

    def get_queryset(self):
        return DataSource.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='test-connection')
    def test_connection(self, request, pk=None):
        """DataSourceTestConnectionView — проверка подключения к источнику."""
        datasource = self.get_object()
        ok, errors = DataValidatorService.validate_connection_data(
            datasource.type, datasource.connection_data or {}
        )
        if ok:
            return Response({"status": "ok", "message": "Подключение допустимо"})
        return Response(
            {"status": "error", "errors": errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=['post'], url_path='load')
    def load(self, request, pk=None):
        """DataSourceLoadView — запуск загрузки данных в ClickHouse."""
        datasource = self.get_object()
        try:
            result = DataLoaderService.load(datasource)
            return Response({
                "status": "success",
                "rows": result.get("rows", 0),
                "columns": result.get("columns", []),
                "preview": result.get("preview", [])[:20],
            })
        except Exception as e:
            return Response(
                {"status": "error", "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=['get'], url_path='status')
    def load_status(self, request, pk=None):
        """DataSourceStatusView — статус последней загрузки."""
        datasource = self.get_object()
        return Response({
            "id": datasource.pk,
            "last_load_status": datasource.last_load_status,
            "last_load_at": datasource.last_load_at.isoformat() if datasource.last_load_at else None,
            "last_load_error": datasource.last_load_error or None,
            "last_load_rows": datasource.last_load_rows,
        })

    @action(detail=True, methods=['get'], url_path='preview')
    def preview(self, request, pk=None):
        """DataSourcePreviewView — предпросмотр данных (с пагинацией limit/offset)."""
        datasource = self.get_object()
        limit = min(1000, max(1, int(request.query_params.get('limit', 50))))
        offset = max(0, int(request.query_params.get('offset', 0)))
        table_name = f"datasource_{datasource.pk}"
        result = DataPreviewService.preview_table(table_name, limit=limit, offset=offset)
        return Response(result)


# Обратная совместимость
DataSourceListCreateView = DataSourceViewSet