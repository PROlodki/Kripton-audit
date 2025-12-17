from django.shortcuts import render, redirect
from clickhouse_driver import Client
import hashlib

client = Client('localhost')  # или IP сервера

def index(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Хешируем пароль (если в БД хранятся хеши)
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

            # 1. Администратор
            if role == 'admin':
                return redirect('/admin/')

            # 2. Заинтересованное лицо
            if role == 'zl':
                return redirect('/zl/')

            # 3. Обычный пользователь
            return redirect('/user/')

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