from django.core.management.base import BaseCommand
from main.import_counterparties import import_counterparties


class Command(BaseCommand):
    help = 'Excel файлаас харилцагч импортлох'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Excel файлын нэр эсвэл path')

    def handle(self, *args, **options):
        excel_file = options['excel_file']
        
        self.stdout.write(f'\n{excel_file} файлыг уншиж байна...\n')
        
        result = import_counterparties(excel_file)
        
        if result:
            self.stdout.write(self.style.SUCCESS('\n✓ Импортлолт амжилттай дууслаа!'))
            self.stdout.write(f'  Шинээр үүссэн: {result["created"]}')
            self.stdout.write(f'  Шинэчилсэн: {result["updated"]}')
            if result["errors"] > 0:
                self.stdout.write(self.style.WARNING(f'  Алдаа: {result["errors"]}'))
        else:
            self.stdout.write(self.style.ERROR('\n✗ Импортлолт амжилтгүй боллоо.'))
