from django.core.management.base import BaseCommand
from main.models import BankTransaction


class Command(BaseCommand):
    help = 'Хуучин төлбөрийн мэдээлэл дээр income_year утгыг transaction_date-н он-оор тохируулна'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Өөрчлөлт хийхгүйгээр зөвхөн мэдээлэл харуулна',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # income_month байгаа боловч income_year байхгүй төлбөрүүд
        transactions = BankTransaction.objects.filter(
            income_type='STUDENT_PAYMENT',
            income_month__isnull=False,
            income_year__isnull=True
        )
        
        count = transactions.count()
        self.stdout.write(f'\n{count} ширхэг төлбөрийн мэдээлэл олдлоо.\n')
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('Шинэчлэх төлбөрийн мэдээлэл байхгүй.'))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN горимд ажиллаж байна. Өөрчлөлт хийгдэхгүй.\n'))
            for tx in transactions[:5]:  # Эхний 5-ыг харуулна
                year = tx.transaction_date.year
                self.stdout.write(
                    f'  ID {tx.id}: {tx.transaction_date} → income_year={year}, income_month={tx.income_month}'
                )
            if count > 5:
                self.stdout.write(f'  ... болон {count - 5} өөр гүйлгээ')
        else:
            updated = 0
            for tx in transactions:
                tx.income_year = tx.transaction_date.year
                tx.save()
                updated += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ {updated} ширхэг төлбөрийн мэдээлэлд income_year утга тохируулагдлаа.')
            )
