"""
Устгагдсан журналтай холбоотой банкны гүйлгээний ангилал цэвэрлэх
"""
from django.core.management.base import BaseCommand
from main.models import BankTransaction


class Command(BaseCommand):
    help = 'Устгагдсан журналтай холбоотой банкны гүйлгээний ангилал цэвэрлэх'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Бүх банкны гүйлгээний ангилалыг цэвэрлэх (accounting_entry = None бол)',
        )
        parser.add_argument(
            '--orphaned',
            action='store_true',
            help='Зөвхөн устгагдсан журналтай холбоотой ангилалыг цэвэрлэх',
        )

    def handle(self, *args, **options):
        if options['all']:
            # Бүх журнал холбогдоогүй гүйлгээний ангилал цэвэрлэх
            transactions = BankTransaction.objects.filter(
                accounting_entry__isnull=True
            ).exclude(
                income_type__isnull=True,
                income_student__isnull=True,
                income_month__isnull=True,
                income_sale__isnull=True
            )
            
            self.stdout.write(f'Олдсон гүйлгээ: {transactions.count()}')
            
            updated = 0
            for tx in transactions:
                if tx.income_type or tx.income_student or tx.income_month or tx.income_sale:
                    tx.income_type = None
                    tx.income_student = None
                    tx.income_month = None
                    tx.income_sale = None
                    tx.offset_account = None
                    tx.is_processed = False
                    tx.save(update_fields=[
                        'income_type', 'income_student', 'income_month', 
                        'income_sale', 'offset_account', 'is_processed'
                    ])
                    updated += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ {updated} гүйлгээний ангилал цэвэрлэгдлээ.')
            )
        
        elif options['orphaned']:
            # Устгагдсан accounting_entry-тэй холбоотой ангилал цэвэрлэх
            # (accounting_entry_id байгаа боловч тухайн entry устсан)
            from main.models import AccountingEntry
            
            all_entry_ids = set(AccountingEntry.objects.values_list('id', flat=True))
            transactions = BankTransaction.objects.filter(
                accounting_entry_id__isnull=False
            )
            
            orphaned = []
            for tx in transactions:
                if tx.accounting_entry_id not in all_entry_ids:
                    orphaned.append(tx)
            
            self.stdout.write(f'Устгагдсан журналтай гүйлгээ: {len(orphaned)}')
            
            for tx in orphaned:
                tx.accounting_entry = None
                tx.offset_account = None
                tx.income_type = None
                tx.income_student = None
                tx.income_month = None
                tx.income_sale = None
                tx.is_processed = False
                tx.save(update_fields=[
                    'accounting_entry', 'offset_account', 'income_type', 
                    'income_student', 'income_month', 'income_sale', 'is_processed'
                ])
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ {len(orphaned)} гүйлгээний ангилал цэвэрлэгдлээ.')
            )
        
        else:
            self.stdout.write(
                self.style.WARNING(
                    'Аргумент сонгоно уу:\n'
                    '  --all       : Журнал холбогдоогүй бүх ангилалыг цэвэрлэх\n'
                    '  --orphaned  : Устгагдсан журналтай холбоотой ангилалыг цэвэрлэх'
                )
            )
