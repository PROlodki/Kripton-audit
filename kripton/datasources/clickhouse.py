from clickhouse_driver import Client
from django.conf import settings

client = Client(
    host=settings.CLICKHOUSE_HOST,
    user=settings.CLICKHOUSE_USER,
    password=settings.CLICKHOUSE_PASSWORD,
    database=settings.CLICKHOUSE_DB
)
