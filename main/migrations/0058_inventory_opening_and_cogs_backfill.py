"""Бараа материалын дансыг засах.

1. "150101 Бараа материал" дансны эхний үлдэгдэл = барааны эхний үлдэгдлийн нийт дүн
   (тоо × нэгжийн өртөг). Барааны эхний үлдэгдлийг оруулсан ч данс 0 хэвээр байсан.
2. Борлуулалтын өртгийн бичилт "5101" гэсэн байхгүй дансны кодоос болж үүсдэггүй байсан.
   Систем эхлэх огнооноос хойших борлуулалтуудад алдагдсан бичилтийг нөхнө:
   Дт 610101 Борлуулсан бүтээгдэхүүний өртөг / Кт 150101 Бараа материал.
3. Дансны дебит/кредит үлдэгдлийг шинэ үеийн журналаар дахин тооцоолно.
"""
from decimal import Decimal

from django.db import migrations
from django.db.models import Sum


def forwards(apps, schema_editor):
    ChartOfAccounts = apps.get_model('main', 'ChartOfAccounts')
    Product = apps.get_model('main', 'Product')
    Sale = apps.get_model('main', 'Sale')
    AccountingEntry = apps.get_model('main', 'AccountingEntry')
    FinanceSettings = apps.get_model('main', 'FinanceSettings')

    inventory = ChartOfAccounts.objects.filter(code='150101').first()
    cogs = ChartOfAccounts.objects.filter(code='610101').first()
    if not inventory:
        return

    # 1) Бараа материалын дансны эхний үлдэгдэл
    total = sum((p.initial_stock * (p.purchase_price or Decimal('0')) for p in Product.objects.all()), Decimal('0'))
    if inventory.opening_balance == 0 and total:
        inventory.opening_balance = total.quantize(Decimal('0.01'))
        inventory.save(update_fields=['opening_balance'])

    settings_obj = FinanceSettings.objects.filter(pk=1).first()
    start = settings_obj.books_start_date if settings_obj else None

    # 2) Алдагдсан өртгийн бичилт
    if cogs and start:
        sales = (Sale.objects.filter(sale_date__gte=start).exclude(status='CANCELLED')
                 .exclude(expected_payment_method='Дотоод хэрэгцээ'))
        for sale in sales:
            number = f'COGS-{sale.sale_number or sale.id}'
            if AccountingEntry.objects.filter(entry_number=number).exists():
                continue
            cost = Decimal('0')
            for item in sale.items.select_related('product'):
                cost += item.quantity * (item.product.purchase_price or Decimal('0'))
            if cost <= 0:
                continue
            AccountingEntry.objects.create(
                entry_date=sale.sale_date, entry_number=number,
                description=f'Борлуулалтын өртөг - {sale.sale_number}',
                debit_account=cogs, debit_amount=cost,
                credit_account=inventory, credit_amount=cost,
                related_sale=sale,
            )

    # 3) Дансны үлдэгдлийг дахин тооцоолох (historical model-д save() override ажиллахгүй)
    entries = AccountingEntry.objects.all()
    if start:
        entries = entries.filter(entry_date__gte=start)
    debits = dict(entries.values('debit_account').annotate(s=Sum('debit_amount')).values_list('debit_account', 's'))
    credits = dict(entries.values('credit_account').annotate(s=Sum('credit_amount')).values_list('credit_account', 's'))
    for account in ChartOfAccounts.objects.all():
        d = debits.get(account.id) or Decimal('0')
        c = credits.get(account.id) or Decimal('0')
        if account.debit_balance != d or account.credit_balance != c:
            account.debit_balance = d
            account.credit_balance = c
            account.save(update_fields=['debit_balance', 'credit_balance'])


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0057_default_bank_fee_rule'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
