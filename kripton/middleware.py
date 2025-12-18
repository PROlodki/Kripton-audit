import jwt
from django.shortcuts import redirect
from django.conf import settings

class JWTMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        path = request.path

        # Публичные страницы
        public_paths = ['/auth/', '/logout/']

        if path in public_paths:
            return self.get_response(request)

        token = request.COOKIES.get('jwt')

        if not token:
            return redirect('/auth/')

        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGO])
        except Exception:
            return redirect('/auth/')

        role = payload.get('role')

        # Проверка ролей
        if path.startswith('/admin/') and role != 'admin':
            return redirect('/auth/')
        if path.startswith('/zl/') and role != 'zl':
            return redirect('/auth/')
        if path.startswith('/user/') and role != 'user':
            return redirect('/auth/')

        request.jwt_payload = payload

        return self.get_response(request)

