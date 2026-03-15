from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User


class RegistrationSerializer(serializers.ModelSerializer):
    """ Сериализация регистрации пользователя и создания нового. """

    # Убедитесь, что пароль содержит не менее 8 символов, не более 128,
    # и так же что он не может быть прочитан клиентской стороной
    password = serializers.CharField(
        max_length=128,
        min_length=8,
        write_only=True
    )

    # Клиентская сторона не должна иметь возможность отправлять токен вместе с
    # запросом на регистрацию. Сделаем его доступным только на чтение.
    token = serializers.CharField(max_length=255, read_only=True)

    class Meta:
        model = User
        # Перечислить все поля, которые могут быть включены в запрос
        # или ответ, включая поля, явно указанные выше.
        fields = ['email', 'username', 'password', 'token']

    def create(self, validated_data):
        # Использовать метод create_user, который мы
        # написали ранее, для создания нового пользователя.
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=255)
    username = serializers.CharField(max_length=255, read_only=True)
    password = serializers.CharField(max_length=128, write_only=True)
    token = serializers.CharField(max_length=255, read_only=True)

    def validate(self, data):
        # В методе validate мы убеждаемся, что текущий экземпляр
        # LoginSerializer значение valid. В случае входа пользователя в систему
        # это означает подтверждение того, что присутствуют адрес электронной
        # почты и то, что эта комбинация соответствует одному из пользователей.
        email = data.get('email', None)
        password = data.get('password', None)

        # Вызвать исключение, если не предоставлена почта.
        if email is None:
            raise serializers.ValidationError(
                'An email address is required to log in.'
            )

        # Вызвать исключение, если не предоставлен пароль.
        if password is None:
            raise serializers.ValidationError(
                'A password is required to log in.'
            )

        # Метод authenticate предоставляется Django и выполняет проверку, что
        # предоставленные почта и пароль соответствуют какому-то пользователю в
        # нашей базе данных. Мы передаем email как username, так как в модели
        # пользователя USERNAME_FIELD = email.
        user = authenticate(username=email, password=password)

        # Если пользователь с данными почтой/паролем не найден, то authenticate
        # вернет None. Возбудить исключение в таком случае.
        if user is None:
            raise serializers.ValidationError(
                'A user with this email and password was not found.'
            )

        # Django предоставляет флаг is_active для модели User. Его цель
        # сообщить, был ли пользователь деактивирован или заблокирован.
        # Проверить стоит, вызвать исключение в случае True.
        if not user.is_active:
            raise serializers.ValidationError(
                'This user has been deactivated.'
            )

        # Лог аудита: успешный вход
        request = self.context.get('request')
        if request:
            from kripton.audit import log_audit
            log_audit(request=request, action_type='login', user=user, details={'email': user.email})

        return {
            'email': user.email,
            'username': user.username,
            'token': user.token
        }

def _user_role(user):
    """Роль для разграничения доступа: admin | stakeholder | user."""
    if user.is_staff or user.is_superuser:
        return 'admin'
    from Reports.models import ReportType
    if ReportType.objects.filter(stakeholders=user).exists():
        return 'stakeholder'
    return 'user'


class UserSerializer(serializers.ModelSerializer):
    """ Сериализация и десериализация User; для текущего пользователя добавляется role. """

    password = serializers.CharField(
        max_length=128,
        min_length=8,
        write_only=True
    )
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'token', 'role')
        read_only_fields = ('token', 'role')

    def get_role(self, obj):
        return _user_role(obj)

    def update(self, instance, validated_data):
        """ Выполняет обновление User. """

        # В отличие от других полей, пароли не следует обрабатывать с помощью
        # setattr. Django предоставляет функцию, которая обрабатывает пароли
        # хешированием и 'солением'. Это означает, что нам нужно удалить поле
        # пароля из словаря 'validated_data' перед его использованием далее.
        password = validated_data.pop('password', None)

        for key, value in validated_data.items():
            # Для ключей, оставшихся в validated_data мы устанавливаем значения
            # в текущий экземпляр User по одному.
            setattr(instance, key, value)

        if password is not None:
            # 'set_password()' решает все вопросы, связанные с безопасностью
            # при обновлении пароля, потому нам не нужно беспокоиться об этом.
            instance.set_password(password)

        # После того, как все было обновлено, мы должны сохранить наш экземпляр
        # User. Стоит отметить, что set_password() не сохраняет модель.
        instance.save()

        return instance


class AdminCreateUserSerializer(serializers.Serializer):
    """Валидация данных для создания пользователя админом (с подразделением и ЗЛ)."""
    user = serializers.DictField()
    user_type = serializers.ChoiceField(
        choices=[('user', 'Пользователь'), ('stakeholder', 'Заинтересованное лицо')],
        default='user',
    )
    department_id = serializers.IntegerField(required=False, allow_null=True)
    report_type_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        if attrs.get('user_type') == 'stakeholder' and not attrs.get('report_type_ids'):
            raise serializers.ValidationError(
                {'report_type_ids': 'Для ЗЛ необходимо выбрать хотя бы один тип отчёта.'}
            )
        return attrs

    def validate_user(self, value):
        email = value.get('email')
        password = value.get('password')
        if not email:
            raise serializers.ValidationError('email обязателен')
        if not password or len(password) < 8:
            raise serializers.ValidationError('пароль не менее 8 символов')
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('Пользователь с таким email уже существует')
        return value