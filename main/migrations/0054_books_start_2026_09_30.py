"""Санхүү, бараа материалын бүртгэлийг 2026-09-30-аас шинээр эхлүүлэх.

- Систем эхлэх огноо = 2026-09-30 (энэ өдрөөс хойших гүйлгээ шинэ үед)
- Хуучин эхний үлдэгдлүүдийг (данс, бараа) FinanceSettings.legacy_opening_snapshot-д
  хадгалаад 0 болгоно — шинэ эхний үлдэгдлийг хэрэглэгч гараар оруулна
- Дансны дебит/кредит үлдэгдлийг зөвхөн шинэ үеийн журналаар дахин тооцоолно

Буцаахад (migrate main 0053) хуучин эхний үлдэгдлүүд сэргээгдэж, бүх журналаар
үлдэгдэл дахин тооцогдоно.
"""
import datetime
from decimal import Decimal

from django.db import migrations
from django.db.models import Sum

START_DATE = datetime.date(2026, 9, 30)


def _recalculate(apps, start_date):
    AccountingEntry = apps.get_model('main', 'AccountingEntry')
    ChartOfAccounts = apps.get_model('main', 'ChartOfAccounts')
    entries = AccountingEntry.objects.all()
    if start_date:
        entries = entries.filter(entry_date__gte=start_date)
    debits = dict(entries.values('debit_account').annotate(s=Sum('debit_amount')).values_list('debit_account', 's'))
    credits = dict(entries.values('credit_account').annotate(s=Sum('credit_amount')).values_list('credit_account', 's'))
    for account in ChartOfAccounts.objects.all():
        account.debit_balance = debits.get(account.id) or Decimal('0')
        account.credit_balance = credits.get(account.id) or Decimal('0')
        account.save(update_fields=['debit_balance', 'credit_balance'])


def forwards(apps, schema_editor):
    FinanceSettings = apps.get_model('main', 'FinanceSettings')
    ChartOfAccounts = apps.get_model('main', 'ChartOfAccounts')
    Product = apps.get_model('main', 'Product')

    snapshot = {
        'created_for_start_date': START_DATE.isoformat(),
        'accounts': {
            str(a.id): {'code': a.code, 'opening_balance': str(a.opening_balance)}
            for a in ChartOfAccounts.objects.exclude(opening_balance=0)
        },
        'products': {
            str(p.id): {'code': p.code, 'initial_stock': p.initial_stock}
            for p in Product.objects.exclude(initial_stock=0)
        },
    }

    settings_obj, _ = FinanceSettings.objects.get_or_create(pk=1)
    settings_obj.books_start_date = START_DATE
    settings_obj.legacy_opening_snapshot = snapshot
    settings_obj.save()

    ChartOfAccounts.objects.update(opening_balance=0)
    Product.objects.update(initial_stock=0)
    _recalculate(apps, START_DATE)


def backwards(apps, schema_editor):
    FinanceSettings = apps.get_model('main', 'FinanceSettings')
    ChartOfAccounts = apps.get_model('main', 'ChartOfAccounts')
    Product = apps.get_model('main', 'Product')

    settings_obj = FinanceSettings.objects.filter(pk=1).first()
    snapshot = (settings_obj.legacy_opening_snapshot if settings_obj else {}) or {}
    for account_id, data in snapshot.get('accounts', {}).items():
        ChartOfAccounts.objects.filter(id=account_id).update(opening_balance=Decimal(data['opening_balance']))
    for product_id, data in snapshot.get('products', {}).items():
        Product.objects.filter(id=product_id).update(initial_stock=data['initial_stock'])
    if settings_obj:
        settings_obj.books_start_date = None
        settings_obj.save()
    _recalculate(apps, None)


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0053_finance_settings'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
