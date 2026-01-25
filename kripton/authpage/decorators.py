from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
import jwt
from django.conf import settings

User = get_user_model()


def role_required(allowed_roles):
    """
    Декоратор для проверки роли пользователя.
    Использование: @role_required(['admin']) или @role_required(['admin', 'zl'])
    
    Args:
        allowed_roles: список разрешенных ролей
    
    Returns:
        redirect на /auth/ если роль не подходит
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Публичные страницы
            if request.path in ['/auth/', '/logout/']:
                return view_func(request, *args, **kwargs)
            
            # Получаем токен из заголовка Authorization
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            token = None
            
            if auth_header.startswith('Token '):
                token = auth_header.split(' ')[1]
            elif auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            
            # Если нет токена в заголовке, проверяем cookies (для обратной совместимости)
            if not token:
                token = request.COOKIES.get('jwt')
            
            if not token:
                return redirect('/auth/')
            
            try:
                # Декодируем токен
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                
                # Проверяем тип токена
                if payload.get('type') != 'access':
                    return redirect('/auth/')
                
                # Получаем пользователя
                user_id = payload.get('id')
                if not user_id:
                    return redirect('/auth/')
                
                try:
                    user = User.objects.get(pk=user_id)
                except User.DoesNotExist:
                    return redirect('/auth/')
                
                # Проверяем активность пользователя
                if not user.is_active:
                    return redirect('/auth/')
                
                # Проверяем роль из токена или из модели пользователя
                user_role = payload.get('role') or getattr(user, 'role', None)
                
                if user_role not in allowed_roles:
                    return redirect('/auth/')
                
                # Добавляем пользователя в request для удобства
                request.user = user
                request.user_role = user_role
                
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
                return redirect('/auth/')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def admin_required(view_func):
    """Декоратор для проверки роли администратора"""
    return role_required(['admin'])(view_func)


def zl_required(view_func):
    """Декоратор для проверки роли ZL"""
    return role_required(['zl'])(view_func)


def user_required(view_func):
    """Декоратор для проверки роли пользователя"""
    return role_required(['user'])(view_func)
