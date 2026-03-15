"""
NotificationService — отправка уведомлений: email, внутренние (аудит), напоминания о сроках.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Email-уведомления, внутренние уведомления (через лог), напоминания о сроках."""

    @staticmethod
    def send_email(to_emails: list, subject: str, body: str, fail_silently: bool = True) -> int:
        """
        Отправить email через Django. Возвращает количество отправленных писем.
        Настройте EMAIL_* в settings (или по умолчанию письма не уйдут).
        """
        if not to_emails:
            return 0
        try:
            return send_mail(
                subject=subject[:998],
                message=body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@localhost'),
                recipient_list=to_emails,
                fail_silently=fail_silently,
            )
        except Exception as e:
            logger.warning("NotificationService send_email failed: %s", e)
            return 0

    @staticmethod
    def notify_internal(user, message: str, resource_type: str = '', resource_id: str = ''):
        """
        Внутреннее уведомление в системе — запись в лог аудита с типом other и details.message.
        Пользователь увидит его в истории/логах.
        """
        try:
            from kripton.audit import log_audit
            log_audit(
                request=None,
                action_type='other',
                resource_type=resource_type or 'notification',
                resource_id=resource_id,
                details={'notification': message},
                user=user,
            )
        except Exception as e:
            logger.warning("NotificationService notify_internal failed: %s", e)

    @staticmethod
    def get_report_request_reminders(days_ahead: int = 3):
        """
        Напоминания о сроках сдачи отчётов: запросы с deadline в ближайшие days_ahead дней.
        Возвращает список ReportRequest для отправки напоминаний.
        """
        from Reports.models import ReportRequest
        today = timezone.now().date()
        end = today + timedelta(days=days_ahead)
        return ReportRequest.objects.filter(
            status__in=['pending', 'approved', 'in_progress'],
            deadline__isnull=False,
            deadline__gte=today,
            deadline__lte=end,
        ).select_related('requester', 'department', 'report_type')

    @staticmethod
    def send_deadline_reminders(days_ahead: int = 3) -> int:
        """
        Отправить email-напоминания по заявкам с приближающимся deadline.
        Возвращает количество отправленных писем.
        Вызывать из cron или management command.
        """
        requests = NotificationService.get_report_request_reminders(days_ahead=days_ahead)
        sent = 0
        for req in requests:
            email = getattr(req.requester, 'email', None)
            if not email:
                continue
            subject = f"Напоминание: срок сдачи отчёта «{req.title}» — {req.deadline}"
            body = (
                f"Здравствуйте.\n\n"
                f"Напоминаем о сроке сдачи отчёта: {req.title}.\n"
                f"Тип: {req.report_type.name if req.report_type_id else '-'}\n"
                f"Срок: {req.deadline}.\n\n"
                f"С уважением,\nСистема отчётности."
            )
            sent += NotificationService.send_email([email], subject, body)
        return sent
