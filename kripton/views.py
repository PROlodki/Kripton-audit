from django.shortcuts import render, redirect
from clickhouse_driver import Client
from django.conf import settings
import hashlib
import jwt

client = Client('localhost')  # или IP сервера


def index(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Хешируем пароль
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Запрос в ClickHouse
        query = """
            SELECT role FROM users
            WHERE username = %(username)s AND password = %(password)s
            LIMIT 1
        """

        result = client.execute(query, {
            'username': username,
            'password': password_hash
        })

        if result:
            role = result[0][0]

            # Создаём JWT-токен
            payload = {
                "username": username,
                "role": role,
            }

            token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGO)

            # Отправляем токен в cookie
            response = redirect(f'/{role}/')
            response.set_cookie(
                "jwt",
                token,
                httponly=True,
                samesite="Strict",
            )
            return response

        return render(request, 'authorization/auth.html', {
            'error': 'Неверный логин или пароль'
        })

    return render(request, 'authorization/auth.html')


def admin(request):
    return render(request, 'administrator/administrator.html')


def zl(request):
    return render(request, 'zl/zl.html')


def user(request):
    return render(request, 'user/user.html')


def logout_view(request):
    response = redirect('/auth/')
    response.delete_cookie('jwt')
    return response
