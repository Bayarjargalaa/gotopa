"""Систем эхлэх огнооноос хойших борлуулалтуудын дагалдах бичлэгийг борлуулалттай холбох.

Өмнө нь барааны хөдөлгөөн (StockMovement.sale) болон журнал (AccountingEntry.related_sale)
борлуулалттай холбогддоггүй байсан тул засах/устгахад буцааж чадахгүй байв.
- Журнал: утганд борлуулалтын дугаар (SAL-...) агуулсан бичилт
- Хөдөлгөөн: борлуулалт үүссэн мөчөөс өмнөх 10 минутад үүссэн, ижил бараа/тоотой OUT хөдөлгөөн
"""
from datetime import timedelta

from django.db import migrations


def forwards(apps, schema_editor):
    Sale = apps.get_model('main', 'Sale')
    StockMovement = apps.get_model('main', 'StockMovement')
    AccountingEntry = apps.get_model('main', 'AccountingEntry')
    FinanceSettings = apps.get_model('main', 'FinanceSettings')

    settings_obj = FinanceSettings.objects.filter(pk=1).first()
    start = settings_obj.books_start_date if settings_obj else None
    if not start:
        return

    for sale in Sale.objects.filter(sale_date__gte=start).exclude(sale_number=''):
        AccountingEntry.objects.filter(
            related_sale__isnull=True, description__contains=sale.sale_number
        ).update(related_sale=sale)

        if StockMovement.objects.filter(sale=sale).exists():
            continue
        needed = [(item.product_id, item.quantity) for item in sale.items.all()]
        candidates = list(StockMovement.objects.filter(
            sale__isnull=True, movement_type='OUT',
            created_at__gte=sale.created_at - timedelta(minutes=10),
            created_at__lte=sale.created_at + timedelta(minutes=2),
        ).order_by('-created_at'))
        matched = []
        for product_id, qty in needed:
            for mv in candidates:
                if mv.id not in matched and mv.product_id == product_id and mv.quantity == qty:
                    matched.append(mv.id)
                    break
        # Бүх бараа таарсан үед л холбоно (буруу холбохоос сэргийлнэ)
        if needed and len(matched) == len(needed):
            StockMovement.objects.filter(id__in=matched).update(sale=sale)


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0058_inventory_opening_and_cogs_backfill'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
