"""
PermissionService — проверка доступа к отчётам и подразделениям.
"""
from django.contrib.auth import get_user_model
from kripton.guide.models import Department

User = get_user_model()


class PermissionService:
    """Права доступа: отчёты, подразделения, список подразделений пользователя."""

    @staticmethod
    def check_report_access(user, report) -> bool:
        """
        Проверка доступа к отчёту: создатель, заинтересованное лицо типа отчёта, staff/superuser.
        """
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.is_staff:
            return True
        if report.created_by_id == user.id:
            return True
        if report.report_type_id and report.report_type.stakeholders.filter(pk=user.id).exists():
            return True
        return False

    @staticmethod
    def check_department_access(user, department: Department) -> bool:
        """
        Проверка доступа к подразделению: руководитель, staff/superuser, или сотрудник отдела.
        """
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.is_staff:
            return True
        if not department:
            return False
        if department.head_of_department_id == user.id:
            return True
        # Сотрудник отдела (через PersonalData)
        from Reports.models import PersonalData
        if PersonalData.objects.filter(department=department, user=user).exists():
            return True
        return False

    @staticmethod
    def get_user_departments(user) -> list:
        """
        Подразделения пользователя: где он руководитель и/или сотрудник (PersonalData).
        Возвращает список Department.
        """
        if not user or not user.is_authenticated:
            return []
        from kripton.guide.models import Department
        from Reports.models import PersonalData
        qs = Department.objects.none()
        # Руководитель
        qs = qs | Department.objects.filter(head_of_department=user)
        # Сотрудник
        dept_ids = PersonalData.objects.filter(user=user).values_list('department_id', flat=True)
        if dept_ids:
            qs = qs | Department.objects.filter(pk__in=dept_ids)
        return list(qs.distinct())
