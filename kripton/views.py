from django.shortcuts import render, redirect


def index(request):
    return render(request, 'authorization/auth.html')


def dashboard(request):
    """Единая страница дашборда — все функции вручную."""
    return render(request, 'dashboard/index.html')


def admin(request):
    """Панель администратора — все функции вручную."""
    return render(request, 'administrator/administrator.html')


def zl(request):
    """Панель заинтересованного лица — просмотр, утверждение, отчёты."""
    return render(request, 'zl/zl.html')


def user(request):
    """Панель пользователя — мои отчёты и заявки, создание."""
    return render(request, 'user/user.html')


def logout_view(request):
    response = redirect('/auth/')
    response.delete_cookie('jwt')
    return response
