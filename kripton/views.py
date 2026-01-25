from django.shortcuts import render, redirect
from clickhouse_driver import Client
from django.conf import settings
import hashlib
import jwt
from kripton.authpage.decorators import admin_required, zl_required, user_required


def index(request):
    """Страница авторизации - доступна всем"""
    return render(request, 'authorization/auth.html')


@admin_required
def admin(request):
    """Страница администратора - доступна только пользователям с ролью 'admin'"""
    return render(request, 'administrator/administrator.html')


@zl_required
def zl(request):
    """Страница ZL - доступна только пользователям с ролью 'zl'"""
    return render(request, 'zl/zl.html')


@user_required
def user(request):
    """Страница пользователя - доступна только пользователям с ролью 'user'"""
    return render(request, 'user/user.html')


def logout_view(request):
    response = redirect('/auth/')
    response.delete_cookie('jwt')
    return response
