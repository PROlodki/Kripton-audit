from django.core.management.base import BaseCommand
from kripton.clickhouse_schema import init_clickhouse_tables


class Command(BaseCommand):
    help = 'Создать таблицы в ClickHouse для аудита и отчётов (audit_log, report_request_events).'

    def handle(self, *args, **options):
        try:
            tables = init_clickhouse_tables()
            for t in tables:
                self.stdout.write(self.style.SUCCESS(f'Таблица создана/проверена: {t}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка ClickHouse: {e}'))
            raise
