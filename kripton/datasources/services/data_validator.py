"""
DataValidatorService — валидация данных (схема, типы, обязательные поля).
"""
import re
from typing import List, Dict, Any, Optional, Tuple


class ValidationError(Exception):
    """Ошибка валидации данных."""
    def __init__(self, message: str, errors: Optional[List[Dict[str, Any]]] = None):
        self.message = message
        self.errors = errors or []
        super().__init__(message)


class DataValidatorService:
    """Валидация строк/таблиц перед загрузкой или использованием."""

    # Допустимые имена колонок ClickHouse (упрощённо)
    COLUMN_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    @staticmethod
    def validate_column_names(columns: List[str]) -> Tuple[bool, List[str]]:
        """
        Проверить имена колонок (длина, символы).
        Возвращает (ok, list of error messages).
        """
        errors = []
        for i, col in enumerate(columns):
            if not col or not isinstance(col, str):
                errors.append(f"Колонка {i}: пустое или не строка")
                continue
            if len(col) > 100:
                errors.append(f"Колонка '{col[:50]}...': длина > 100")
            if not DataValidatorService.COLUMN_NAME_PATTERN.match(col.replace(' ', '_')):
                errors.append(f"Колонка '{col}': недопустимые символы")
        return (len(errors) == 0, errors)

    @staticmethod
    def validate_row_lengths(rows: List[List[Any]], expected_columns: int) -> Tuple[bool, List[str]]:
        """Проверить, что у всех строк одинаковое число колонок."""
        errors = []
        for i, row in enumerate(rows):
            if len(row) != expected_columns:
                errors.append(f"Строка {i + 1}: ожидалось {expected_columns} колонок, получено {len(row)}")
        return (len(errors) == 0, errors)

    @staticmethod
    def validate_csv_path(path: str) -> Tuple[bool, List[str]]:
        """Проверить путь к CSV (существование, расширение)."""
        errors = []
        if not path or not isinstance(path, str):
            errors.append("Путь к файлу не указан")
            return (False, errors)
        import os
        if not os.path.isfile(path):
            errors.append(f"Файл не найден: {path}")
        if not path.lower().endswith('.csv'):
            errors.append("Ожидается файл с расширением .csv")
        return (len(errors) == 0, errors)

    @staticmethod
    def validate_connection_data(datasource_type: str, connection_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Валидация connection_data в зависимости от типа источника.
        Возвращает (ok, list of error messages).
        """
        errors = []
        if not connection_data or not isinstance(connection_data, dict):
            return (False, ["connection_data должен быть словарём"])

        if datasource_type == 'csv':
            path = connection_data.get('path') or connection_data.get('file')
            ok, path_errors = DataValidatorService.validate_csv_path(path or '')
            if not ok:
                errors.extend(path_errors)
        elif datasource_type == 'postgres':
            for key in ('host', 'database', 'user'):
                if not connection_data.get(key):
                    errors.append(f"Для PostgreSQL необходимо указать: {key}")
        elif datasource_type == 'gsheet':
            if not connection_data.get('sheet_id') and not connection_data.get('url'):
                errors.append("Для Google Sheets укажите sheet_id или url")

        return (len(errors) == 0, errors)

    @staticmethod
    def validate_report_data(data: Any) -> Tuple[bool, List[str]]:
        """
        Валидация данных отчёта (report.data).
        Допустимы: dict, list of dict; значения — примитивы или вложенные dict/list.
        """
        errors = []
        if data is None:
            return (True, [])
        if isinstance(data, dict):
            if len(data) > 1000:
                errors.append("Слишком много ключей в данных отчёта")
            return (len(errors) == 0, errors)
        if isinstance(data, list):
            if len(data) > 10000:
                errors.append("Слишком много строк в данных отчёта")
            for i, item in enumerate(data[:100]):
                if not isinstance(item, (dict, list, str, int, float, bool)) and item is not None:
                    errors.append(f"Элемент {i}: недопустимый тип {type(item).__name__}")
            return (len(errors) == 0, errors)
        errors.append("Данные отчёта должны быть dict или list")
        return (False, errors)
