"""
StockMovement (OUT, sale__isnull=True) баримтуудыг Sale + SaleItem болгон шилжүүлэх
"""
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from django.db import transaction
from main.models import StockMovement, Sale, SaleItem

movements = StockMovement.objects.filter(
    movement_type='OUT', sale__isnull=True
).select_related('product', 'counterparty', 'salesperson', 'created_by').order_by('created_at')

print(f'Шилжүүлэх баримт: {movements.count()}')

created = 0
errors = 0

for mv in movements:
    try:
        with transaction.atomic():
            # Борлуулалтын дугаар = reference_number эсвэл auto
            sale_number = mv.reference_number or f'MIG-{mv.id}'
            if Sale.objects.filter(sale_number=sale_number).exists():
                sale_number = f'{sale_number}-MIG{mv.id}'

            sale = Sale.objects.create(
                sale_number=sale_number,
                customer=mv.counterparty,
                sale_date=mv.created_at.date(),
                status='COMPLETED',
                total_amount=mv.total_amount,
                paid_amount=mv.total_amount,
                notes=mv.notes or '',
                salesperson_name=mv.customer_name or '',
                created_by=mv.created_by,
            )

            SaleItem.objects.create(
                sale=sale,
                product=mv.product,
                quantity=mv.quantity,
                unit_price=mv.price,
            )

            # StockMovement-ийг Sale-тай холбох
            mv.sale = sale
            mv.save(update_fields=['sale'])

            created += 1
    except Exception as e:
        errors += 1
        print(f'  АЛДАА {mv.id} ({mv.reference_number}): {e}')

print(f'\nДууслаа: {created} борлуулалт үүссэн, {errors} алдаа')
