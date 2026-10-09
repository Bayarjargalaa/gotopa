from django.core.management.base import BaseCommand

from main.bank_dedup import find_duplicates, remove_duplicate


class Command(BaseCommand):
    help = 'Давхцсан хуулга импортлосноор давхардсан банкны гүйлгээг харуулах (--apply: устгах)'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Давхардлыг бодитоор устгана')

    def handle(self, *args, **options):
        groups = find_duplicates()
        if not groups:
            self.stdout.write(self.style.SUCCESS('Давхардсан гүйлгээ алга.'))
            return

        removed = 0
        manual = []
        for g in groups:
            keep = g['keep'][0]
            self.stdout.write(
                f"{keep.bank_account.code} {keep.transaction_date} {keep.description[:45]} "
                f"+{keep.income_amount:,.0f} -{keep.expense_amount:,.0f}"
            )
            for tx in g['keep']:
                self.stdout.write(f"    үлдэнэ  #{tx.id}{' (журнал ' + tx.accounting_entry.entry_number + ')' if tx.accounting_entry_id else ''}")
            for tx in g['remove']:
                tx_id = tx.id  # устгасны дараа None болно
                entry = f" + журнал {tx.accounting_entry.entry_number}" if tx.accounting_entry_id else ''
                if options['apply']:
                    reasons = remove_duplicate(tx)
                    if reasons:
                        manual.append((tx, reasons))
                        self.stdout.write(self.style.WARNING(f"    ГАРААР  #{tx_id}: {', '.join(reasons)}"))
                    else:
                        removed += 1
                        self.stdout.write(self.style.SUCCESS(f"    устгасан #{tx_id}{entry}"))
                else:
                    self.stdout.write(f"    устгана #{tx_id}{entry}")

        total = sum(len(g['remove']) for g in groups)
        if options['apply']:
            self.stdout.write(self.style.SUCCESS(f'\n{removed} давхардал устгагдлаа.'))
            if manual:
                self.stdout.write(self.style.WARNING(f'{len(manual)} нь холболттой тул гараар шалгана уу.'))
        else:
            self.stdout.write(f'\n{len(groups)} бүлэг, {total} давхардал. Устгахдаа --apply нэмж ажиллуулна.')
