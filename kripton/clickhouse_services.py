"""
Сервисы записи данных в ClickHouse для отчётов и дашбордов.
При недоступности ClickHouse ошибки логируются, работа Django не прерывается.
"""
import json
import logging
from datetime import datetime

from kripton.datasources.clickhouse import get_client
from kripton.clickhouse_schema import AUDIT_LOG_TABLE, REPORT_REQUEST_EVENTS_TABLE

logger = logging.getLogger(__name__)


def _safe_execute(statement, params=None):
    try:
        get_client().execute(statement, params=params)
    except Exception as e:
        logger.warning("ClickHouse write failed: %s", e, exc_info=True)


def push_audit_log(
    timestamp,
    user_id=None,
    username='',
    action_type='other',
    resource_type='',
    resource_id='',
    details=None,
    ip_address=None,
    user_agent='',
    department_id=None,
    department_name='',
    department_code='',
):
    """Записать одну запись лога аудита в ClickHouse."""
    if details is None:
        details = {}
    details_str = json.dumps(details, ensure_ascii=False)
    if isinstance(timestamp, datetime) and timestamp.tzinfo:
        ts = timestamp.astimezone(None).replace(tzinfo=None)
    else:
        ts = timestamp
    _safe_execute(
        f"""
        INSERT INTO {AUDIT_LOG_TABLE} (
            timestamp, user_id, username, action_type, resource_type, resource_id,
            details, ip_address, user_agent, department_id, department_name, department_code
        ) VALUES
        """,
        [(
            ts,
            user_id,
            username or '',
            action_type or 'other',
            (resource_type or '')[:100],
            (resource_id or '')[:100],
            details_str,
            ip_address,
            (user_agent or '')[:500],
            department_id,
            department_name or '',
            department_code or '',
        )],
    )


def push_report_request_event(request_obj):
    """
    Записать снимок заявки на отчёт в ClickHouse для дашбордов.
    Вызывать при создании/обновлении ReportRequest (например в post_save).
    """
    try:
        created = request_obj.created_at
        event_date = created.date() if created and hasattr(created, 'date') else None
        requester = request_obj.requester
        dept = getattr(request_obj, 'department', None)
        rt = getattr(request_obj, 'report_type', None)
        approved_at = request_obj.approved_at
        completed_at = request_obj.completed_at
        # ClickHouse принимает datetime; при timezone-aware приводим к naive UTC для единообразия
        if approved_at and getattr(approved_at, 'tzinfo', None):
            from django.utils import timezone
            approved_at = timezone.make_naive(approved_at, timezone=timezone.utc)
        if completed_at and getattr(completed_at, 'tzinfo', None):
            from django.utils import timezone
            completed_at = timezone.make_naive(completed_at, timezone=timezone.utc)
        row = (
            event_date,
            created,
            request_obj.id,
            requester.id if requester else None,
            str(requester) if requester else '',
            dept.id if dept else None,
            dept.name if dept else '',
            (dept.code or '') if dept else '',
            rt.id if rt else None,
            rt.name if rt else '',
            (rt.code or '') if rt else '',
            request_obj.status,
            (request_obj.title or '')[:255],
            approved_at,
            completed_at,
        )
        _safe_execute(
            f"""
            INSERT INTO {REPORT_REQUEST_EVENTS_TABLE} (
                event_date, created_at, request_id, requester_id, requester_name,
                department_id, department_name, department_code,
                report_type_id, report_type_name, report_type_code,
                status, title, approved_at, completed_at
            ) VALUES
            """,
            [row],
        )
    except Exception as e:
        logger.warning("push_report_request_event failed: %s", e, exc_info=True)
