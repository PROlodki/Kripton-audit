"""
ReportService — создание, отправка, утверждение, экспорт и валидация отчётов.
"""
from django.utils import timezone

from Reports.models import Report, ReportType
from Reports.export import export_report
from kripton.datasources.services import DataValidatorService


class ReportService:
    """Единая точка бизнес-логики по отчётам."""

    @staticmethod
    def create_report(*, title: str, report_type: ReportType, description: str = '',
                     created_by, data: dict = None, clickhouse_table: str = '',
                     clickhouse_query: str = '') -> Report:
        """Создать отчёт."""
        report = Report.objects.create(
            title=title,
            report_type=report_type,
            description=description or '',
            created_by=created_by,
            data=data or {},
            clickhouse_table=clickhouse_table or '',
            clickhouse_query=clickhouse_query or '',
        )
        return report

    @staticmethod
    def submit_report(report: Report) -> Report:
        """Отправить отчёт (установить submitted_at)."""
        if report.submitted_at:
            raise ValueError("Отчет уже отправлен")
        report.submitted_at = timezone.now()
        report.save(update_fields=['submitted_at'])
        return report

    @staticmethod
    def approve_report(report: Report, approved_by) -> Report:
        """Утвердить отчёт."""
        report.approved_at = timezone.now()
        report.approved_by = approved_by
        report.save(update_fields=['approved_at', 'approved_by'])
        return report

    @staticmethod
    def generate_pdf(report: Report):
        """Сгенерировать PDF. Возвращает (content_type, filename, content: bytes)."""
        return export_report(report, 'pdf')

    @staticmethod
    def generate_excel(report: Report):
        """Сгенерировать Excel. Возвращает (content_type, filename, content: bytes)."""
        return export_report(report, 'xlsx')

    @staticmethod
    def generate_word(report: Report):
        """Сгенерировать Word. Возвращает (content_type, filename, content: bytes)."""
        return export_report(report, 'docx')

    @staticmethod
    def validate_report(report: Report) -> tuple:
        """
        Валидация данных отчёта (report.data).
        Возвращает (ok: bool, errors: list[str]).
        """
        ok, errors = DataValidatorService.validate_report_data(report.data)
        return ok, errors
