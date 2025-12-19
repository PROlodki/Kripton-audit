from django.shortcuts import render, redirect
from clickhouse_driver import Client
from django.conf import settings
import hashlib
import jwt




def index(request):
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
