"""
DataLoaderService — универсальный загрузчик данных в ClickHouse.
Поддерживает CSV; заготовка под PostgreSQL и Google Sheets.
"""
import os
import logging
from django.utils import timezone

from kripton.datasources.clickhouse import get_client, execute_safe
from kripton.datasources.models import DataSource

logger = logging.getLogger(__name__)


class DataLoaderService:
    """Универсальный загрузчик: загрузка из источника в ClickHouse по типу DataSource."""

    @staticmethod
    def load(datasource: DataSource) -> dict:
        """
        Загрузить данные источника в ClickHouse.
        Обновляет datasource.last_load_* и возвращает результат.
        """
        table_name = f"datasource_{datasource.pk}"
        datasource.last_load_status = 'loading'
        datasource.last_load_error = ''
        datasource.save(update_fields=['last_load_status', 'last_load_error'])

        try:
            if datasource.type == 'csv':
                result = DataLoaderService._load_csv(datasource, table_name)
            elif datasource.type == 'postgres':
                result = DataLoaderService._load_postgres(datasource, table_name)
            elif datasource.type == 'gsheet':
                result = DataLoaderService._load_gsheet(datasource, table_name)
            else:
                raise ValueError(f"Тип источника не поддерживается: {datasource.type}")

            datasource.last_load_status = 'success'
            datasource.last_load_at = timezone.now()
            datasource.last_load_error = ''
            datasource.last_load_rows = result.get('rows', 0)
            datasource.save(update_fields=[
                'last_load_status', 'last_load_at', 'last_load_error', 'last_load_rows'
            ])
            return result
        except Exception as e:
            logger.exception("DataLoaderService load failed")
            datasource.last_load_status = 'error'
            datasource.last_load_at = timezone.now()
            datasource.last_load_error = str(e)[:2000]
            datasource.last_load_rows = None
            datasource.save(update_fields=[
                'last_load_status', 'last_load_at', 'last_load_error', 'last_load_rows'
            ])
            raise

    @staticmethod
    def _load_csv(datasource: DataSource, table_name: str) -> dict:
        """Загрузка из CSV: connection_data = {'path': '...'} или {'file_id': ...}."""
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("Установите pandas для загрузки CSV: pip install pandas")

        conn = datasource.connection_data or {}
        path = conn.get('path') or conn.get('file')
        if not path or not os.path.isfile(path):
            raise FileNotFoundError(f"Файл не найден: {path}")

        df = pd.read_csv(path)
        if df.empty:
            return {'rows': 0, 'columns': [], 'preview': []}

        columns = [str(c).strip().replace(' ', '_')[:100] for c in df.columns]
        client = get_client()
        col_defs = ", ".join([f"`{c}` String" for c in columns])
        client.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} ({col_defs}) ENGINE = MergeTree ORDER BY tuple()"
        )
        # Очистка перед вставкой (простая перезапись)
        client.execute(f"TRUNCATE TABLE IF EXISTS {table_name}")
        rows = df.fillna('').astype(str).values.tolist()
        if rows:
            client.execute(f"INSERT INTO {table_name} VALUES", rows)

        return {
            'rows': len(rows),
            'columns': columns,
            'preview': df.head(50).fillna('').astype(str).values.tolist(),
        }

    @staticmethod
    def _load_postgres(datasource: DataSource, table_name: str) -> dict:
        """Загрузка из PostgreSQL: connection_data = {host, port, db, user, password, query или table}."""
        raise NotImplementedError(
            "Загрузка из PostgreSQL запланирована. Используйте CSV или реализуйте через pandas.read_sql."
        )

    @staticmethod
    def _load_gsheet(datasource: DataSource, table_name: str) -> dict:
        """Загрузка из Google Sheets: connection_data = {sheet_id, range, credentials}."""
        raise NotImplementedError(
            "Загрузка из Google Sheets запланирована. Используйте CSV или экспорт в CSV."
        )
