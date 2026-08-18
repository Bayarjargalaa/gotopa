"""
Борлуулалтад холбогдсон банк/кассын гүйлгээнүүдийн орлогын журнал болон
эсрэг дансыг (510101 Борлуулалтын орлого) тэнцүүлэх.

- Журнал үүсээгүй гүйлгээнд Дт банк/касс — Кт 510101 бичилт үүсгэнэ
- Журнал үүссэн ч эсрэг данс хоосон гүйлгээнд 510101-ийг бөглөнө
- Сурагчийн төлбөртэй хосолсон, эсвэл өөр дансаар гараар ангилсан гүйлгээг хөндөхгүй
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef, Q

from main.import_bank_transactions import sync_sale_revenue_journal
from main.models import BankTransaction, SalePaymentAllocation


class Command(BaseCommand):
    help = 'Борлуулалттай холбогдсон гүйлгээнүүдийн орлогын журнал/эсрэг дансыг тэнцүүлэх'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Юу өөрчлөгдөхийг л харуулна, өгөгдлийг хөндөхгүй',
        )
        parser.add_argument(
            '--user',
            default=None,
            help='Журналын бичилтийг үүсгэсэн хэрэглэгчийн username (default: эхний superuser)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if options['user']:
            user = User.objects.filter(username=options['user']).first()
            if not user:
                self.stderr.write(f'Хэрэглэгч "{options["user"]}" олдсонгүй.')
                return
        else:
            user = User.objects.filter(is_superuser=True).order_by('id').first()

        transactions = BankTransaction.objects.annotate(
            has_sale_alloc=Exists(SalePaymentAllocation.objects.filter(transaction=OuterRef('pk')))
        ).filter(
            Q(has_sale_alloc=True) | Q(income_sale__isnull=False)
        ).select_related(
            'bank_account', 'offset_account', 'accounting_entry'
        ).order_by('transaction_date', 'id')

        self.stdout.write(f'Борлуулалттай холбоотой гүйлгээ: {transactions.count()}')

        stats = {'created': 0, 'updated': 0, 'offset': 0, 'deleted': 0, 'skipped': 0}
        labels = {
            'created': 'журнал үүсгэх',
            'updated': 'журналын дүн шинэчлэх',
            'offset': 'эсрэг данс 510101 бөглөх',
            'deleted': 'журнал устгах',
        }

        for tx in transactions:
            entry_number = tx.accounting_entry.entry_number if tx.accounting_entry else '—'
            result = sync_sale_revenue_journal(tx, user, dry_run=dry_run)
            stats[result] = stats.get(result, 0) + 1

            if result == 'skipped':
                continue

            if not dry_run:
                tx.refresh_from_db()
                entry_number = tx.accounting_entry.entry_number if tx.accounting_entry else '—'

            self.stdout.write(
                f'  [{labels[result]}] #{tx.id} {tx.transaction_date} '
                f'{tx.income_amount:,.0f}₮ · {entry_number} · {tx.description[:30]}'
            )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            'ДҮН: журнал үүссэн={created}, дүн шинэчилсэн={updated}, '
            'эсрэг данс бөглөсөн={offset}, устгасан={deleted}, хөндөөгүй={skipped}'.format(**stats)
        ))
        if dry_run:
            self.stdout.write('(--dry-run — өгөгдөл хөндөгдөөгүй)')
