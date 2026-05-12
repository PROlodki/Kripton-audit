from django.utils import timezone
from rest_framework import status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .renders import UserJSONRender
from .serializers import (
    LoginSerializer, RegistrationSerializer, UserSerializer, AdminCreateUserSerializer,
)


class RegistrationAPIView(APIView):
    """
    Разрешить всем пользователям (аутентифицированным и нет) доступ к данному эндпоинту.
    """
    permission_classes = (AllowAny,)
    renderer_classes = (UserJSONRender,)
    serializer_class = RegistrationSerializer

    def post(self, request):
        user = request.data.get('user', {})

        # Паттерн создания сериализатора, валидации и сохранения - довольно
        # стандартный, и его можно часто увидеть в реальных проектах.
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    permission_classes = (AllowAny,)
    renderer_classes = (UserJSONRender,)
    serializer_class = LoginSerializer

    def post(self, request):
        user = request.data.get('user', {})

        # Обратите внимание, что мы не вызываем метод save() сериализатора, как
        # делали это для регистрации. Дело в том, что в данном случае нам
        # нечего сохранять. Вместо этого, метод validate() делает все нужное.
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

class UserRetrieveUpdateAPIView(RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = (UserJSONRender,)
    serializer_class = UserSerializer

    def retrieve(self, request, *args, **kwargs):
        # Здесь нечего валидировать или сохранять. Мы просто хотим, чтобы
        # сериализатор обрабатывал преобразования объекта User во что-то, что
        # можно привести к json и вернуть клиенту.
        serializer = self.serializer_class(request.user)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        serializer_data = request.data.get('user', {})

        # Паттерн сериализации, валидирования и сохранения - то, о чем говорили
        serializer = self.serializer_class(
            request.user, data=serializer_data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminCreateUserAPIView(APIView):
    """Список пользователей (GET) и создание пользователя/ЗЛ (POST) — только для админа."""
    permission_classes = (IsAuthenticated, IsAdminUser,)

    def get(self, request):
        """Список пользователей: id, username, email, role, department_id, report_type_ids (для ЗЛ)."""
        from .models import User
        from Reports.models import PersonalData, ReportType
        users = User.objects.filter(is_active=True).order_by('email')
        results = []
        for u in users:
            role = 'admin' if (u.is_staff or u.is_superuser) else (
                'stakeholder' if ReportType.objects.filter(stakeholders=u).exists() else 'user'
            )
            pd = PersonalData.objects.filter(user=u).first()
            department_id = pd.department_id if pd else None
            report_type_ids = list(
                ReportType.objects.filter(stakeholders=u).values_list('id', flat=True)
            )
            results.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'role': role,
                'department_id': department_id,
                'report_type_ids': report_type_ids,
            })
        return Response({'results': results})

    def post(self, request):
        serializer = AdminCreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user_data = data['user']
        department_id = data.get('department_id')
        report_type_ids = data.get('report_type_ids') or []

        from .models import User
        user_type = data.get('user_type', 'user')
        user = User.objects.create_user(
            email=user_data['email'],
            username=user_data.get('username') or user_data['email'],
            password=user_data['password'],
        )
        if department_id:
            from kripton.guide.models import Department
            from Reports.models import PersonalData
            department = Department.objects.filter(pk=department_id).first()
            if department:
                PersonalData.objects.create(
                    user=user,
                    department=department,
                    last_name=user_data.get('last_name') or user.username,
                    first_name=user_data.get('first_name') or '',
                    position=user_data.get('position') or '',
                    hire_date=user_data.get('hire_date') or timezone.now().date(),
                )
        if user_type == 'stakeholder':
            for rt_id in report_type_ids:
                from Reports.models import ReportType
                rt = ReportType.objects.filter(pk=rt_id).first()
                if rt:
                    rt.stakeholders.add(user)
        resp_serializer = UserSerializer(user)
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


class AdminUserDetailAPIView(APIView):
    """Просмотр и редактирование пользователя админом: подразделение, типы отчётов (ЗЛ)."""
    permission_classes = (IsAuthenticated, IsAdminUser,)

    def get(self, request, pk):
        from .models import User
        from Reports.models import PersonalData, ReportType
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response({'detail': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        role = 'admin' if (user.is_staff or user.is_superuser) else (
            'stakeholder' if ReportType.objects.filter(stakeholders=user).exists() else 'user'
        )
        pd = PersonalData.objects.filter(user=user).first()
        department_id = pd.department_id if pd else None
        report_type_ids = list(
            ReportType.objects.filter(stakeholders=user).values_list('id', flat=True)
        )
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': role,
            'department_id': department_id,
            'report_type_ids': report_type_ids,
        })

    def patch(self, request, pk):
        from .models import User
        from kripton.guide.models import Department
        from Reports.models import PersonalData, ReportType
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response({'detail': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        department_id = request.data.get('department_id')
        report_type_ids = request.data.get('report_type_ids')
        if department_id is not None:
            department = Department.objects.filter(pk=department_id).first()
            pd = PersonalData.objects.filter(user=user).first()
            if department:
                if pd:
                    pd.department = department
                    pd.save(update_fields=['department'])
                else:
                    PersonalData.objects.create(
                        user=user,
                        department=department,
                        last_name=user.username or '',
                        first_name='',
                        position='',
                        hire_date=timezone.now().date(),
                    )
            elif pd:
                pd.department = None
                pd.save(update_fields=['department'])
        if report_type_ids is not None:
            current_ids = set(
                ReportType.objects.filter(stakeholders=user).values_list('id', flat=True)
            )
            new_ids = set()
            for x in report_type_ids:
                try:
                    new_ids.add(int(x))
                except (TypeError, ValueError):
                    pass
            to_add = new_ids - current_ids
            to_remove = current_ids - new_ids
            for rt_id in to_remove:
                rt = ReportType.objects.filter(pk=rt_id).first()
                if rt:
                    rt.stakeholders.remove(user)
            for rt_id in to_add:
                rt = ReportType.objects.filter(pk=rt_id).first()
                if rt:
                    rt.stakeholders.add(user)
        return self.get(request, pk)

    def delete(self, request, pk):
        from .models import User
        from Reports.models import ReportType
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response({'detail': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        if user.pk == request.user.pk:
            return Response({'detail': 'Нельзя удалить себя'}, status=status.HTTP_400_BAD_REQUEST)
        if user.is_superuser:
            return Response({'detail': 'Нельзя удалить суперпользователя'}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = False
        user.save(update_fields=['is_active'])
        for rt in ReportType.objects.filter(stakeholders=user):
            rt.stakeholders.remove(user)

        return Response(status=status.HTTP_204_NO_CONTENT)