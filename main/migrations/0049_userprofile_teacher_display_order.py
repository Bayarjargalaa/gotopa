from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0048_teacherlevel'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='teacher_display_order',
            field=models.PositiveIntegerField(default=9999, verbose_name='Багшийн жагсаалтын дараалал'),
        ),
    ]
