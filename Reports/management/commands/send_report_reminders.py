"""Напоминания о сроках сдачи отчётов (вызов из cron)."""
from django.core.management.base import BaseCommand
from kripton.notifications.services import NotificationService


class Command(BaseCommand):
    help = 'Отправить email-напоминания по заявкам с приближающимся deadline (по умолчанию 3 дня).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=3, help='За сколько дней до срока напоминать')

    def handle(self, *args, **options):
        days = options['days']
        sent = NotificationService.send_deadline_reminders(days_ahead=days)
        self.stdout.write(self.style.SUCCESS(f'Отправлено напоминаний: {sent}'))
