"""
Создание статичного пользователя-админа для входа на любую страницу.
Логин: admin@kripton.local  Пароль: admin
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

# Статичные учётные данные (для разработки/демо)
STATIC_ADMIN_EMAIL = 'admin@kripton.local'
STATIC_ADMIN_USERNAME = 'admin'
STATIC_ADMIN_PASSWORD = 'admin'


class Command(BaseCommand):
    help = 'Создать статичного админа (admin@kripton.local / admin) с полным доступом'

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            email=STATIC_ADMIN_EMAIL,
            defaults={
                'username': STATIC_ADMIN_USERNAME,
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        if created:
            user.set_password(STATIC_ADMIN_PASSWORD)
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f'Создан админ: {STATIC_ADMIN_EMAIL} / пароль: {STATIC_ADMIN_PASSWORD}'
            ))
        else:
            user.set_password(STATIC_ADMIN_PASSWORD)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f'Админ обновлён: {STATIC_ADMIN_EMAIL} / пароль: {STATIC_ADMIN_PASSWORD}'
            ))
