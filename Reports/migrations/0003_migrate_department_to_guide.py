# Migration: switch ReportRequest and PersonalData department FK to guide.Department

import django.db.models.deletion
from django.db import migrations, models


def migrate_departments_to_guide(apps, schema_editor):
    """Copy Reports.Department rows to guide.Department and update FKs."""
    from django.utils import timezone
    ReportsDepartment = apps.get_model('Reports', 'Department')
    GuideDepartment = apps.get_model('guide', 'Department')
    ReportRequest = apps.get_model('Reports', 'ReportRequest')
    PersonalData = apps.get_model('Reports', 'PersonalData')

    old_id_to_new = {}
    for old in ReportsDepartment.objects.all():
        new_dept = GuideDepartment.objects.create(
            name=old.name,
            code=getattr(old, 'code', None) or None,
            description=(getattr(old, 'description', '') or '')[:255],
            head_of_department_id=getattr(old, 'head_id', None),
            created_at=getattr(old, 'created_at', None) or timezone.now(),
            is_active=True,
        )
        old_id_to_new[old.id] = new_dept.id

    for req in ReportRequest.objects.all():
        if req.department_id and req.department_id in old_id_to_new:
            req.department_new_id = old_id_to_new[req.department_id]
            req.save(update_fields=['department_new_id'])

    for pd in PersonalData.objects.filter(department_id__isnull=False):
        if pd.department_id in old_id_to_new:
            pd.department_new_id = old_id_to_new[pd.department_id]
            pd.save(update_fields=['department_new_id'])


def reverse_migrate(apps, schema_editor):
    """Reverse not fully supported (Reports.Department would be recreated in next migration)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('Reports', '0002_personaldata'),
        ('guide', '0002_department_code_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportrequest',
            name='department_new',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='guide.department', verbose_name='Подразделение'),
        ),
        migrations.AddField(
            model_name='personaldata',
            name='department_new',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='guide.department', verbose_name='Отдел'),
        ),
        migrations.RunPython(migrate_departments_to_guide, reverse_migrate),
        migrations.RemoveField(model_name='reportrequest', name='department'),
        migrations.RemoveField(model_name='personaldata', name='department'),
        migrations.RenameField(model_name='reportrequest', old_name='department_new', new_name='department'),
        migrations.RenameField(model_name='personaldata', old_name='department_new', new_name='department'),
        migrations.AlterField(
            model_name='reportrequest',
            name='department',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='report_requests', to='guide.department', verbose_name='Подразделение'),
        ),
        migrations.AlterField(
            model_name='personaldata',
            name='department',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='personnel', to='guide.department', verbose_name='Отдел'),
        ),
    ]
