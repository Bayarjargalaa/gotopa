from django.core.management.base import BaseCommand
from main.import_bank_transactions import import_bank_transactions


class Command(BaseCommand):
    help = 'Банкны хуулгын Excel файлаас гүйлгээ импортлох'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Excel файлын нэр эсвэл path')
        parser.add_argument('--account', type=str, default='Голомт банк', help='Банкны дансны нэр')

    def handle(self, *args, **options):
        excel_file = options['excel_file']
        account_name = options['account']
        
        self.stdout.write(f'\n{excel_file} файлыг уншиж байна...')
        self.stdout.write(f'Данс: {account_name}\n')
        
        result = import_bank_transactions(excel_file, account_name=account_name)
        
        if result:
            self.stdout.write(self.style.SUCCESS('\n✓ Импортлолт амжилттай дууслаа!'))
            self.stdout.write(f'  Үүссэн гүйлгээ: {result["created"]}')
            self.stdout.write(f'  Алгассан: {result["skipped"]}')
            if result["errors"] > 0:
                self.stdout.write(self.style.WARNING(f'  Алдаа: {result["errors"]}'))
            self.stdout.write(f'  Дансны шинэ үлдэгдэл: {result["final_balance"]:,.0f}₮')
        else:
            self.stdout.write(self.style.ERROR('\n✗ Импортлолт амжилтгүй боллоо.'))
