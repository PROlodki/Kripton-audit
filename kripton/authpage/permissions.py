from rest_framework import permissions


class IsRoleAdmin(permissions.BasePermission):
    """
    Разрешение только для пользователей с ролью 'admin'.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role == 'admin'
        )


class IsRoleZL(permissions.BasePermission):
    """
    Разрешение только для пользователей с ролью 'zl'.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role == 'zl'
        )


class IsRoleUser(permissions.BasePermission):
    """
    Разрешение только для пользователей с ролью 'user'.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role == 'user'
        )


class HasRole(permissions.BasePermission):
    """
    Разрешение для проверки наличия одной из указанных ролей.
    Использование: permission_classes = [HasRole(['admin', 'zl'])]
    """
    def __init__(self, allowed_roles):
        self.allowed_roles = allowed_roles

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role in self.allowed_roles
        )
