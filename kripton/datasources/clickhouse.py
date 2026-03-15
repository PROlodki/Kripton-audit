from clickhouse_driver import Client
from django.conf import settings

# Нативный клиент для запросов к ClickHouse
_client = None


def get_client():
    """Возвращает клиент ClickHouse (ленивая инициализация при первом вызове)."""
    global _client
    if _client is None:
        _client = Client(
            host=settings.CLICKHOUSE_HOST,
            port=getattr(settings, 'CLICKHOUSE_PORT', 9000),
            user=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD,
            database=settings.CLICKHOUSE_DB,
            connect_timeout=getattr(settings, 'CLICKHOUSE_CONNECT_TIMEOUT', 10),
        )
    return _client


# Для обратной совместимости: client — тот же объект, но создаётся при первом обращении
class _LazyClient:
    def __getattr__(self, name):
        return getattr(get_client(), name)

    def execute(self, *args, **kwargs):
        return get_client().execute(*args, **kwargs)


client = _LazyClient()


def execute_safe(query, params=None, with_column_types=False):
    """
    Выполнить запрос к ClickHouse. При ошибке подключения возвращает пустой список.
    Удобно для кода, который должен работать и без запущенного ClickHouse.
    """
    try:
        return get_client().execute(query, params=params, with_column_types=with_column_types)
    except Exception:
        return [] if not with_column_types else ([], [])
