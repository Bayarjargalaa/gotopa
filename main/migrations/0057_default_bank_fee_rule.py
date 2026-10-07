"""Анхдагч автомат холболтын загвар: банкны шимтгэл, хураамж → 702701 / 1.2.9.

Өмнөх 362 шимтгэлийн гүйлгээний утгаас гаргав: "Charges for PORD Customer Payment",
"Гүйлгээний шимтгэл", "ДАНС ХӨТӨЛСНИЙ ХУРААМЖ", "СЕТТЛЕМЕНТИЙН ШИМТГЭЛ СУУТГАВ".
"""
from django.db import migrations


def forwards(apps, schema_editor):
    AutoLinkRule = apps.get_model('main', 'AutoLinkRule')
    ChartOfAccounts = apps.get_model('main', 'ChartOfAccounts')
    CashFlowIndicator = apps.get_model('main', 'CashFlowIndicator')
    account = ChartOfAccounts.objects.filter(code='702701').first()
    if not account or AutoLinkRule.objects.exists():
        return
    AutoLinkRule.objects.create(
        name='Банкны шимтгэл, хураамж',
        keywords='шимтгэл, Charges for, хураамж',
        direction='EXPENSE',
        offset_account=account,
        cash_flow_indicator=CashFlowIndicator.objects.filter(code='1.2.9').first(),
        auto_apply=True,
        priority=10,
    )


def backwards(apps, schema_editor):
    apps.get_model('main', 'AutoLinkRule').objects.filter(name='Банкны шимтгэл, хураамж').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0056_auto_link_rule'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
