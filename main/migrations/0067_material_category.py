from django.db import migrations


def create_material_category(apps, schema_editor):
    """Бараа хувиргалтад зарцуулах бэлдэцийн анхдагч ангилал."""
    ProductCategory = apps.get_model('main', 'ProductCategory')
    # SQLite-ийн iexact кирилл үсгийн том/жижгийг ялгадаг тул Python-д харьцуулна
    if not any(c.name.strip().lower() == 'бэлдэц' for c in ProductCategory.objects.all()):
        ProductCategory.objects.create(name='Бэлдэц', description='Бараа хувиргалт (ж: лаа хийх)-д зарцуулах түүхий эд')


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0066_purchase_document_conversion'),
    ]

    operations = [
        migrations.RunPython(create_material_category, migrations.RunPython.noop),
    ]
