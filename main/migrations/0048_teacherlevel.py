from django.db import migrations, models
from django.utils.text import slugify


def create_default_teacher_levels(apps, schema_editor):
    TeacherLevel = apps.get_model('main', 'TeacherLevel')
    TeacherLevel.objects.bulk_create([
        TeacherLevel(name='Сургагч', slug=slugify('Сургагч', allow_unicode=True), sort_order=1),
        TeacherLevel(name='Дадлагажигч', slug=slugify('Дадлагажигч', allow_unicode=True), sort_order=2),
    ])


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0047_userprofile_photo_filename'),
    ]

    operations = [
        migrations.CreateModel(
            name='TeacherLevel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Нэр')),
                ('slug', models.SlugField(max_length=100, unique=True, verbose_name='Код')),
                ('is_active', models.BooleanField(default=True, verbose_name='Идэвхтэй')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='Эрэмбэ')),
            ],
            options={
                'verbose_name': 'Багшийн түвшин',
                'verbose_name_plural': 'Багшийн түвшнүүд',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.RunPython(create_default_teacher_levels, migrations.RunPython.noop),
    ]
