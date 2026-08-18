import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0043_add_accountingentry_related_sale'),
    ]

    operations = [
        migrations.AddField(
            model_name='banktransaction',
            name='transfer_source',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='transfer_mirrors',
                to='main.banktransaction',
                verbose_name='Эх гүйлгээ',
                help_text='Автоматаар үүссэн кассын эсрэг мөр бол үүсгэсэн банк/кассын гүйлгээ',
            ),
        ),
    ]
