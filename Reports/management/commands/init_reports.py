from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from Reports.models import ReportRequest, Report, ReportType
from kripton.guide.models import Department

class Command(BaseCommand):
    help = 'Инициализация системы отчетов: создание групп и базовых данных'
    
    def handle(self, *args, **kwargs):
        self.create_groups()
        self.create_base_data()
        self.stdout.write(self.style.SUCCESS('Система отчетов успешно инициализирована!'))
    
    def create_groups(self):
        """Создание групп пользователей"""
        groups = [
            ('Администраторы', 'Полный доступ ко всем функциям'),
            ('Менеджеры отчетов', 'Могут утверждать запросы отчетов'),
            ('Пользователи отчетов', 'Могут создавать запросы отчетов'),
            ('Заинтересованные лица', 'Могут просматривать отчеты'),
        ]
        
        for name, description in groups:
            group, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(f'✓ Создана группа: {name}')
        
        # Назначаем разрешения
        self.assign_permissions()
    
    def assign_permissions(self):
        """Назначение разрешений группам"""
        # Разрешения для ReportRequest
        report_request_ct = ContentType.objects.get_for_model(ReportRequest)
        report_request_perms = Permission.objects.filter(content_type=report_request_ct)
        
        # Администраторы - все разрешения
        admin_group = Group.objects.get(name='Администраторы')
        admin_group.permissions.set(report_request_perms)
        
        # Менеджеры - могут просматривать и изменять
        manager_group = Group.objects.get(name='Менеджеры отчетов')
        manager_perms = report_request_perms.filter(
            codename__in=['view_reportrequest', 'change_reportrequest']
        )
        manager_group.permissions.set(manager_perms)
        
        # Пользователи - могут добавлять и просматривать
        user_group = Group.objects.get(name='Пользователи отчетов')
        user_perms = report_request_perms.filter(
            codename__in=['add_reportrequest', 'view_reportrequest']
        )
        user_group.permissions.set(user_perms)
        
        self.stdout.write('✓ Назначены разрешения группам')
    
    def create_base_data(self):
        """Создание базовых данных"""
        # Создаем тестовые отделы, если их нет
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
            
            if not Department.objects.exists():
                departments = [
                    {'name': 'IT отдел', 'code': 'IT', 'head_of_department': admin_user},
                    {'name': 'Финансовый отдел', 'code': 'FIN', 'head_of_department': admin_user},
                    {'name': 'Отдел продаж', 'code': 'SALES', 'head_of_department': admin_user},
                ]
                for dept_data in departments:
                    Department.objects.create(**dept_data)
                self.stdout.write('✓ Созданы базовые отделы')
            
            if not ReportType.objects.exists():
                report_types = [
                    {'name': 'Финансовый отчет', 'code': 'FIN_REPORT', 'description': 'Отчет по финансовым показателям'},
                    {'name': 'Отчет по продажам', 'code': 'SALES_REPORT', 'description': 'Отчет по продажам компании'},
                    {'name': 'Технический отчет', 'code': 'TECH_REPORT', 'description': 'Технический отчет по инфраструктуре'},
                ]
                
                for rt_data in report_types:
                    ReportType.objects.create(**rt_data)
                self.stdout.write('✓ Созданы базовые типы отчетов')
                
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠ Ошибка при создании базовых данных: {e}'))