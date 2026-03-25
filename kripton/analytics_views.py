from rest_framework.views import APIView
from rest_framework.response import Response
from .audit_analytics import (
    get_user_activity,
    get_action_stats,
    get_activity_by_day,
    get_report_status_stats,
    get_reports_by_department,
    get_reports_created_by_day,
)


class AnalyticsView(APIView):
    def get(self, request):
        return Response({
            "user_activity": list(get_user_activity()),
            "actions": list(get_action_stats()),
            "activity_by_day": list(get_activity_by_day()),
            "report_status": list(get_report_status_stats()),
            "reports_by_department": list(get_reports_by_department()),
            "reports_by_day": list(get_reports_created_by_day()),
        })