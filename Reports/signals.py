from django.db.models.signals import post_save
from django.dispatch import receiver

from Reports.models import ReportRequest


@receiver(post_save, sender=ReportRequest)
def report_request_to_clickhouse(sender, instance, **kwargs):
    """При сохранении заявки на отчёт — отправить снимок в ClickHouse для дашбордов."""
    try:
        from kripton.clickhouse_services import push_report_request_event
        push_report_request_event(instance)
    except Exception:
        pass
