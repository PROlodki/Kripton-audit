"""
DataPreviewService — предпросмотр данных из ClickHouse (таблица источника или произвольный запрос).
"""
from typing import List, Any, Optional

from kripton.datasources.clickhouse import get_client, execute_safe


class DataPreviewService:
    """Предпросмотр данных: получение строк и метаданных из таблицы/запроса."""

    @staticmethod
    def preview_table(
        table_name: str,
        limit: int = 50,
        offset: int = 0,
        columns: Optional[List[str]] = None,
    ) -> dict:
        """
        Выбрать строки из таблицы ClickHouse.
        Возвращает: { "columns": [...], "rows": [[...], ...], "total": int или None }.
        total считается отдельным запросом COUNT(*) при limit < 1000.
        """
        safe_limit = max(1, min(1000, limit))
        safe_offset = max(0, offset)

        if columns:
            col_list = ", ".join([f"`{c}`" for c in columns])
            query = f"SELECT {col_list} FROM `{table_name}` LIMIT {safe_limit} OFFSET {safe_offset}"
        else:
            query = f"SELECT * FROM `{table_name}` LIMIT {safe_limit} OFFSET {safe_offset}"

        result = execute_safe(query, with_column_types=True)
        if not result or (isinstance(result, tuple) and not result[0]):
            return {"columns": [], "rows": [], "total": None}

        if isinstance(result, tuple) and len(result) == 2:
            rows, column_types = result
            col_names = [c[0] for c in column_types] if column_types else []
        else:
            rows = result if isinstance(result, list) else []
            col_names = list(rows[0].keys()) if rows and isinstance(rows[0], dict) else []

        # clickhouse_driver возвращает list of tuples при with_column_types
        if rows and isinstance(rows[0], (list, tuple)):
            pass
        else:
            rows = [list(r.values()) if isinstance(r, dict) else r for r in rows]

        total = None
        if safe_offset == 0 and safe_limit < 1000:
            try:
                cnt = execute_safe(f"SELECT count() FROM `{table_name}`")
                total = cnt[0][0] if cnt and cnt[0] is not None else None
            except Exception:
                pass

        return {
            "columns": col_names,
            "rows": rows,
            "total": total,
        }

    @staticmethod
    def preview_query(query: str, limit: int = 500) -> dict:
        """
        Выполнить произвольный SELECT-запрос (ограничен limit) и вернуть columns + rows.
        Для безопасности лучше не принимать сырой query от клиента, а строить его на сервере.
        """
        if ';' in query.strip().rstrip(';'):
            query = query.split(';')[0].strip()
        if not query.upper().strip().startswith('SELECT'):
            return {"columns": [], "rows": [], "error": "Допустимы только SELECT-запросы"}

        if "LIMIT" not in query.upper():
            query = f"{query.rstrip()} LIMIT {max(1, min(1000, limit))}"

        result = execute_safe(query, with_column_types=True)
        if not result:
            return {"columns": [], "rows": []}

        if isinstance(result, tuple) and len(result) == 2:
            rows, column_types = result
            col_names = [c[0] for c in column_types]
        else:
            rows = result if isinstance(result, list) else []
            col_names = list(rows[0].keys()) if rows and isinstance(rows[0], dict) else []

        if rows and isinstance(rows[0], (list, tuple)):
            pass
        else:
            rows = [list(r.values()) if isinstance(r, dict) else r for r in rows]

        return {"columns": col_names, "rows": rows}
