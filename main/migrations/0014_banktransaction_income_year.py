"""
Банкны гүйлгээний орлогын он нэмэх
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0013_banktransaction_income_month_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='banktransaction',
            name='income_year',
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text='Хэддүгээр оны төлбөр (жишээ: 2026)',
                null=True,
                verbose_name='Төлбөрийн он'
            ),
        ),
    ]
