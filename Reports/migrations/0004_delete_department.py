# Remove Reports.Department — all data and FKs moved to guide.Department

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Reports', '0003_migrate_department_to_guide'),
    ]

    operations = [
        migrations.DeleteModel(name='Department'),
    ]
