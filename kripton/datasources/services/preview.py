# Обратная совместимость: предпросмотр через DataPreviewService
from .data_preview import DataPreviewService


def preview_table(table_name, limit=50):
    """Возвращает список строк (как раньше) для обратной совместимости."""
    result = DataPreviewService.preview_table(table_name, limit=limit)
    return result.get("rows", [])
