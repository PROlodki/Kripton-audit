from django.db import models
import jwt
import secrets
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)


class UserManager(BaseUserManager):

    def create_user(self, username, email, password=None):
        """ Создает и возвращает пользователя с имэйлом, паролем и именем. """
        if username is None:
            raise TypeError('Users must have a username.')

        if email is None:
            raise TypeError('Users must have an email address.')

        user = self.model(username=username, email=self.normalize_email(email))
        user.set_password(password)
        user.save()

        return user

    def create_superuser(self, username, email, password):
        """ Создает и возввращет пользователя с привилегиями суперадмина. """
        if password is None:
            raise TypeError('Superusers must have a password.')

        user = self.create_user(username, email, password)
        user.is_superuser = True
        user.is_staff = True
        user.save()

        return user


class RefreshToken(models.Model):
    """Модель для хранения refresh токенов"""
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='refresh_tokens'
    )
    token = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)

    class Meta:
        db_table = 'refresh_tokens'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'is_revoked']),
        ]

    def __str__(self):
        return f"RefreshToken for {self.user.email}"

    def is_valid(self):
        """Проверяет, действителен ли токен"""
        return not self.is_revoked and datetime.utcnow() < self.expires_at

    @classmethod
    def create_for_user(cls, user, days=30):
        """Создает новый refresh токен для пользователя"""
        # Генерируем случайный токен
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=days)
        
        refresh_token = cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
        return refresh_token


class User(AbstractBaseUser, PermissionsMixin):
    # Каждому пользователю нужен понятный человеку уникальный идентификатор,
    # который мы можем использовать для предоставления User в пользовательском
    # интерфейсе. Мы так же проиндексируем этот столбец в базе данных для
    # повышения скорости поиска в дальнейшем.
    username = models.CharField(db_index=True, max_length=255, unique=True)
    # Так же мы нуждаемся в поле, с помощью которого будем иметь возможность
    # связаться с пользователем и идентифицировать его при входе в систему.
    # Поскольку адрес почты нам нужен в любом случае, мы также будем
    # использовать его для входы в систему, так как это наиболее
    # распространенная форма учетных данных на данный момент (ну еще телефон).
    email = models.EmailField(db_index=True, unique=True)

    # Когда пользователь более не желает пользоваться нашей системой, он может
    # захотеть удалить свой аккаунт. Для нас это проблема, так как собираемые
    # нами данные очень ценны, и мы не хотим их удалять :) Мы просто предложим
    # пользователям способ деактивировать учетку вместо ее полного удаления.
    # Таким образом, они не будут отображаться на сайте, но мы все еще сможем
    # далее анализировать информацию.
    is_active = models.BooleanField(default=True)

    # Этот флаг определяет, кто может войти в административную часть нашего
    # сайта. Для большинства пользователей это флаг будет ложным.
    is_staff = models.BooleanField(default=False)

    # Временная метка создания объекта.
    created_at = models.DateTimeField(auto_now_add=True)

    # Временная метка показывающая время последнего обновления объекта.
    updated_at = models.DateTimeField(auto_now=True)

    # Роль пользователя: admin, zl, user
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('zl', 'ZL'),
        ('user', 'Пользователь'),
    ]
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='user',
        db_index=True,
        help_text='Роль пользователя определяет доступ к различным разделам системы'
    )

    # Дополнительный поля, необходимые Django
    # при указании кастомной модели пользователя.

    # Свойство USERNAME_FIELD сообщает нам, какое поле мы будем использовать
    # для входа в систему. В данном случае мы хотим использовать почту.
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    # Сообщает Django, что определенный выше класс UserManager
    # должен управлять объектами этого типа.
    objects = UserManager()

    def __str__(self):
        """ Строковое представление модели (отображается в консоли) """
        return self.email

    @property
    def token(self):
        """
        Позволяет получить токен пользователя путем вызова user.token, вместо
        user._generate_jwt_token(). Декоратор @property выше делает это
        возможным. token называется "динамическим свойством".
        """
        return self._generate_access_token()

    @property
    def refresh_token(self):
        """
        Создает и возвращает новый refresh токен для пользователя.
        """
        return self._generate_refresh_token()

    def get_full_name(self):
        """
        Этот метод требуется Django для таких вещей, как обработка электронной
        почты. Обычно это имя фамилия пользователя, но поскольку мы не
        используем их, будем возвращать username.
        """
        return self.username

    def get_short_name(self):
        """ Аналогично методу get_full_name(). """
        return self.username

    def _generate_access_token(self):
        """
        Генерирует access токен (JWT), в котором хранится идентификатор этого
        пользователя. Срок действия токена — 1 день.
        """
        dt = datetime.utcnow() + timedelta(days=1)

        payload = {
            'id': self.pk,
            'type': 'access',
            'role': self.role,  # Включаем роль в токен
            'exp': dt,  # Можно передать datetime, PyJWT сам конвертирует
        }

        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

        # PyJWT >= 2.0 возвращает строку, старые — bytes
        if isinstance(token, bytes):
            token = token.decode('utf-8')

        return token

    def _generate_refresh_token(self):
        """
        Создает и возвращает новый refresh токен для пользователя.
        Срок действия refresh токена — 30 дней.
        """
        # Отзываем старые токены пользователя (опционально, можно оставить несколько)
        # RefreshToken.objects.filter(user=self, is_revoked=False).update(is_revoked=True)
        
        # Создаем новый refresh токен
        refresh_token = RefreshToken.create_for_user(self, days=30)
        return refresh_token.token