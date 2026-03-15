from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Reports'
    verbose_name = 'Отчеты'

    def ready(self):
        import Reports.signals  # noqa: F401 — регистрация сигналов для ClickHouse
