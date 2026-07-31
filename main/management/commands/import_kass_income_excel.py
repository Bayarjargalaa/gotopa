from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from collections import defaultdict

import pandas as pd
from django.core.management.base import BaseCommand, CommandError

from main.models import BankTransaction, ChartOfAccounts


class Command(BaseCommand):
    help = 'Кассын орлогын Excel (kass.xlsx) файлаас зөвхөн орлогыг импортлох'

    @staticmethod
    def _parse_excel_date(value):
        """Excel-ийн A баганад буй огнооны утгыг date төрөл рүү хөрвүүлнэ."""
        if pd.isna(value):
            return None

        if isinstance(value, date) and not isinstance(value, datetime):
            return value

        if isinstance(value, datetime):
            return value.date()

        parsed = pd.to_datetime(value, errors='coerce', dayfirst=True)
        if pd.isna(parsed):
            return None

        return parsed.date()

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Excel файлын зам (жишээ: kass.xlsx)')
        parser.add_argument('--account-code', type=str, default='100100', help='Кассын дансны код (default: 100100)')
        parser.add_argument('--date', type=str, default=None, help='Импортлох огноо YYYY-MM-DD (өгөхгүй бол өнөөдөр)')
        parser.add_argument(
            '--fix-existing-date-from',
            type=str,
            default=None,
            help='Өмнө буруу огноотой орсон мөрүүдийг энэ огнооноос авч Excel A баганын огноогоор засна (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--fix-only',
            action='store_true',
            help='Шинэ мөр үүсгэхгүй, зөвхөн --fix-existing-date-from ашиглан огноо засна',
        )
        parser.add_argument('--dry-run', action='store_true', help='Хадгалахгүй, зөвхөн шалгаж тоолно')

    def handle(self, *args, **options):
        excel_file = options['excel_file']
        account_code = options['account_code']
        dry_run = options['dry_run']
        fix_only = options['fix_only']
        fix_from_date = None

        if options['date']:
            try:
                import_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('Огнооны формат буруу байна. YYYY-MM-DD хэлбэрээр оруулна уу.')
        else:
            import_date = date.today()

        if options['fix_existing_date_from']:
            try:
                fix_from_date = datetime.strptime(options['fix_existing_date_from'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('--fix-existing-date-from огнооны формат буруу байна. YYYY-MM-DD хэлбэрээр оруулна уу.')

        if fix_only and not fix_from_date:
            raise CommandError('--fix-only ашиглах бол --fix-existing-date-from огноо заавал өгнө үү.')

        try:
            bank_account = ChartOfAccounts.objects.get(code=account_code)
        except ChartOfAccounts.DoesNotExist:
            raise CommandError(f'{account_code} кодтой данс олдсонгүй.')

        if bank_account.account_type != 'ASSET':
            self.stdout.write(self.style.WARNING(f'⚠️ {bank_account.code} данс ASSET төрөл биш байна: {bank_account.account_type}'))

        self.stdout.write(f'Файл: {excel_file}')
        self.stdout.write(f'Данс: {bank_account.code} - {bank_account.name}')
        if options['date']:
            self.stdout.write(f'Огноо: {import_date} (гараар өгсөн)')
        else:
            self.stdout.write('Огноо: Excel A баганаас мөр тус бүрээр уншина')
        if fix_from_date:
            self.stdout.write(f'Засварлах эх огноо: {fix_from_date}')
        self.stdout.write(f'Горим: {"Зөвхөн засвар" if fix_only else "Импорт + засвар"}')
        self.stdout.write(f'Режим: {"DRY-RUN" if dry_run else "IMPORT"}')

        df_preview = pd.read_excel(excel_file, engine='openpyxl', header=None, nrows=30)
        header_row = None
        for idx, row in df_preview.iterrows():
            if any('Гүйлгээний утга' in str(cell) for cell in row):
                header_row = idx
                break

        if header_row is not None:
            df = pd.read_excel(excel_file, engine='openpyxl', header=header_row)
        else:
            df = pd.read_excel(excel_file, engine='openpyxl')

        if 'Гүйлгээний утга' not in df.columns or 'Орлого' not in df.columns:
            raise CommandError('Файлд "Гүйлгээний утга" болон "Орлого" баганууд олдсонгүй.')

        valid_items = []
        skipped_count = 0
        error_count = 0
        invalid_date_count = 0

        for i, row in df.iterrows():
            try:
                description = str(row.get('Гүйлгээний утга', '')).strip()
                income_raw = row.get('Орлого', 0)

                if not description or description.lower() == 'nan':
                    skipped_count += 1
                    continue

                if pd.isna(income_raw):
                    skipped_count += 1
                    continue

                try:
                    income = Decimal(str(income_raw).replace(',', '').strip())
                except (InvalidOperation, AttributeError):
                    error_count += 1
                    continue

                if income <= 0:
                    skipped_count += 1
                    continue

                if options['date']:
                    transaction_date = import_date
                else:
                    # Хэрэглэгчийн хүсэлтээр A баганаас (0-р индекс) огноог уншина.
                    transaction_date = self._parse_excel_date(row.iloc[0] if len(row) > 0 else None)
                    if transaction_date is None:
                        invalid_date_count += 1
                        skipped_count += 1
                        continue

                valid_items.append({
                    'transaction_date': transaction_date,
                    'description': description,
                    'income': income,
                })
            except Exception:
                error_count += 1

        fixed_count = 0
        fix_unmatched_count = 0
        if fix_from_date:
            # Өмнө буруу огноотой орсон мөрүүдийг description+income occurrence-аар Excel мөртэй тулгаж огноог засна.
            fix_pool = defaultdict(list)
            fix_rows = BankTransaction.objects.filter(
                bank_account=bank_account,
                account_type='CASH',
                bank_name='CASH_REGISTER',
                transaction_date=fix_from_date,
                expense_amount=Decimal('0'),
            ).order_by('id')

            for tx in fix_rows:
                key = (str(tx.description).strip(), Decimal(str(tx.income_amount)))
                fix_pool[key].append(tx)

            used_fix_count = defaultdict(int)

            for item in valid_items:
                fix_key = (item['description'], item['income'])
                use_idx = used_fix_count[fix_key]
                candidates = fix_pool.get(fix_key, [])

                if use_idx >= len(candidates):
                    fix_unmatched_count += 1
                    continue

                tx = candidates[use_idx]
                used_fix_count[fix_key] += 1

                if tx.transaction_date != item['transaction_date']:
                    if not dry_run:
                        tx.transaction_date = item['transaction_date']
                        tx.save(update_fields=['transaction_date'])
                    fixed_count += 1

        # Ижил огноо/тайлбар/дүнтэй мөр олон байж болох тул occurrence-аар нь удирдана.
        existing_counts = {}
        seen_in_file = defaultdict(int)
        created_count = 0

        if not fix_only:
            for item in valid_items:
                transaction_date = item['transaction_date']
                description = item['description']
                income = item['income']

                key = (transaction_date, description, income)
                seen_in_file[key] += 1
                # Энэ key-тай өмнө нь импортлогдсон occurrence тооноос бага/тэнцүү бол алгасна.
                if key not in existing_counts:
                    existing_counts[key] = BankTransaction.objects.filter(
                        bank_account=bank_account,
                        account_type='CASH',
                        bank_name='CASH_REGISTER',
                        transaction_date=transaction_date,
                        expense_amount=Decimal('0'),
                        description=description,
                        income_amount=income,
                    ).count()

                if seen_in_file[key] <= existing_counts[key]:
                    skipped_count += 1
                    continue

                if not dry_run:
                    BankTransaction.objects.create(
                        account_type='CASH',
                        bank_name='CASH_REGISTER',
                        bank_account=bank_account,
                        transaction_date=transaction_date,
                        transaction_time=None,
                        description=description,
                        counterparty_account='',
                        counterparty_name='',
                        income_amount=income,
                        expense_amount=Decimal('0'),
                        is_processed=False,
                        offset_account=None,
                    )

                created_count += 1

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(f'Үүссэн: {created_count}'))
        if fix_from_date:
            self.stdout.write(self.style.SUCCESS(f'Огноо зассан: {fixed_count}'))
            self.stdout.write(self.style.WARNING(f'Засварт тохирох мөр олдоогүй: {fix_unmatched_count}'))
        self.stdout.write(self.style.WARNING(f'Алгассан: {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Алдаа: {error_count}'))
        if invalid_date_count:
            self.stdout.write(self.style.WARNING(f'Огноо танигдаагүй (A багана): {invalid_date_count}'))
        self.stdout.write('=' * 60)
