"""
DataTransformService — трансформация данных перед загрузкой или отдачей.
Нормализация имён колонок, типов, переименование.
"""
import re
from typing import List, Dict, Any


class DataTransformService:
    """Трансформации для имён колонок и строк таблиц."""

    @staticmethod
    def normalize_column_name(name: str, max_length: int = 100) -> str:
        """Привести имя колонки к допустимому виду: буквы, цифры, подчёркивание."""
        if not name or not isinstance(name, str):
            return "col_0"
        s = re.sub(r'[^\w]', '_', name.strip())
        s = re.sub(r'_+', '_', s).strip('_')
        if not s or s[0].isdigit():
            s = 'col_' + s
        return s[:max_length] or 'col_0'

    @staticmethod
    def normalize_columns(columns: List[str]) -> List[str]:
        """Нормализовать список имён колонок (уникальные имена при дубликатах)."""
        seen = {}
        result = []
        for c in columns:
            base = DataTransformService.normalize_column_name(c)
            if base in seen:
                seen[base] += 1
                result.append(f"{base}_{seen[base]}")
            else:
                seen[base] = 0
                result.append(base)
        return result

    @staticmethod
    def row_to_dict(row: List[Any], columns: List[str]) -> Dict[str, Any]:
        """Преобразовать строку в словарь по списку колонок."""
        return dict(zip(columns, row))

    @staticmethod
    def dict_to_row(d: Dict[str, Any], columns: List[str], fill: str = '') -> List[Any]:
        """Преобразовать словарь в строку по порядку колонок."""
        return [d.get(c, fill) for c in columns]

    @staticmethod
    def ensure_string_values(rows: List[List[Any]]) -> List[List[str]]:
        """Привести все ячейки к строкам (для вставки в ClickHouse String)."""
        return [[str(x) if x is not None else '' for x in row] for row in rows]
