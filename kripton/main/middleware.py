from django.shortcuts import redirect

class RoleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        path = request.path

        # Страницы, доступные всем
        public_paths = ['/', '/logout/']

        # Публичные пути пропускаем
        if path in public_paths:
            return self.get_response(request)

        # Если пользователь не авторизован — отправляем на вход
        if not request.session.get('auth'):
            return redirect('/')

        role = request.session.get('role')

        # Правила доступа
        if path.startswith('/admin/') and role != 'admin':
            return redirect('/')
        if path.startswith('/zl/') and role != 'zl':
            return redirect('/')
        if path.startswith('/user/') and role != 'user':
            return redirect('/')

        return self.get_response(request)
