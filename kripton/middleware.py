import jwt
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


class JWTMiddleware:
    """
    Middleware для проверки JWT токенов и прав доступа на основе ролей.
    Поддерживает токены из заголовка Authorization и cookies.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Публичные страницы и API эндпоинты
        public_paths = ['/auth/', '/logout/']
        api_paths = ['/api/']

        # Пропускаем публичные страницы и API (API использует DRF authentication)
        if any(path.startswith(p) for p in public_paths + api_paths):
            return self.get_response(request)

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
            # Декодируем токен используя SECRET_KEY (новая система)
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            except jwt.InvalidTokenError:
                # Пробуем старый JWT_SECRET для обратной совместимости
                try:
                    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGO])
                except Exception:
                    return redirect('/auth/')

            # Проверяем тип токена (если есть в payload)
            token_type = payload.get('type')
            if token_type and token_type != 'access':
                return redirect('/auth/')

            # Получаем роль из токена
            role = payload.get('role')

            # Если роли нет в токене, пытаемся получить из пользователя
            if not role:
                user_id = payload.get('id')
                if user_id:
                    try:
                        user = User.objects.get(pk=user_id)
                        role = getattr(user, 'role', None)
                    except User.DoesNotExist:
                        return redirect('/auth/')
                else:
                    return redirect('/auth/')

            # Проверка прав доступа на основе ролей
            if path.startswith('/admin/') and role != 'admin':
                return redirect('/auth/')
            if path.startswith('/zl/') and role != 'zl':
                return redirect('/auth/')
            if path.startswith('/user/') and role != 'user':
                return redirect('/auth/')

            # Сохраняем payload и роль в request для использования в views
            request.jwt_payload = payload
            request.user_role = role

            # Пытаемся получить пользователя и добавить в request
            user_id = payload.get('id')
            if user_id:
                try:
                    request.user = User.objects.get(pk=user_id)
                except User.DoesNotExist:
                    pass

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
            return redirect('/auth/')

        return self.get_response(request)

