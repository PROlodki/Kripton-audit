"""
Создание RealtimeEvent при смене статуса отчёта/заявки (для SSE).
Вызывать из view/signal после submit/approve/reject.
"""
from kripton.models import RealtimeEvent


def notify_report_status(report, event_type: str, payload: dict = None):
    """
    Создать событие для создателя отчёта и заинтересованных лиц типа отчёта.
    event_type: report_submitted, report_approved, ...
    """
    users_to_notify = set()
    if report.created_by_id:
        users_to_notify.add(report.created_by_id)
    if report.report_type_id:
        for u in report.report_type.stakeholders.values_list('id', flat=True):
            users_to_notify.add(u)
    payload = payload or {}
    payload['report_id'] = report.id
    payload['report_title'] = report.title
    for user_id in users_to_notify:
        RealtimeEvent.objects.create(
            user_id=user_id,
            event_type=event_type,
            payload=payload,
        )


def notify_report_request_status(request_obj, event_type: str, payload: dict = None):
    """
    Создать событие для заявителя и (опционально) руководителя отдела.
    event_type: request_approved, request_rejected, request_completed, ...
    """
    users_to_notify = set()
    if request_obj.requester_id:
        users_to_notify.add(request_obj.requester_id)
    if getattr(request_obj, 'department', None) and request_obj.department.head_of_department_id:
        users_to_notify.add(request_obj.department.head_of_department_id)
    payload = payload or {}
    payload['request_id'] = request_obj.id
    payload['title'] = request_obj.title
    for user_id in users_to_notify:
        RealtimeEvent.objects.create(
            user_id=user_id,
            event_type=event_type,
            payload=payload,
        )
