from clickhouse_driver import Client
from django.conf import settings

client = Client(
    host=settings.CLICKHOUSE_HOST,
    user=settings.CLICKHOUSE_USER,
    password=settings.CLICKHOUSE_PASSWORD,
    database=settings.CLICKHOUSE_DB
)
# Заглушка вместо ClickHouse (отключено)

def get_client():
    return None


class _LazyClient:
    def __getattr__(self, name):
        return None

    def execute(self, *args, **kwargs):
        return []


client = _LazyClient()


def execute_safe(query, params=None, with_column_types=False):
    return [] if not with_column_types else ([], [])

