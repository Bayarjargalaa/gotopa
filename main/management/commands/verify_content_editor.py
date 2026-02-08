from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group

class Command(BaseCommand):
    help = 'Verify bayasaa68@gmail.com user permissions'

    def handle(self, *args, **options):
        try:
            user = User.objects.get(email='bayasaa68@gmail.com')
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Хэрэглэгч олдсон: {user.username}'))
            self.stdout.write(f'  Email: {user.email}')
            self.stdout.write(f'  is_staff: {user.is_staff}')
            self.stdout.write(f'  is_superuser: {user.is_superuser}')
            
            groups = list(user.groups.values_list('name', flat=True))
            self.stdout.write(f'  Groups: {groups}')
            
            has_perm = user.has_perm('main.can_edit_content')
            self.stdout.write(f'  can_edit_content: {has_perm}')
            
            if user.is_staff and has_perm:
                self.stdout.write(self.style.SUCCESS('\n✓ Бүх эрх зөв тохируулагдсан!'))
                self.stdout.write('Хэрэглэгч inline editing хийх боломжтой.')
            else:
                self.stdout.write(self.style.WARNING('\n⚠ Эрх дутуу байна:'))
                if not user.is_staff:
                    self.stdout.write('  - is_staff=False (True байх ёстой)')
                if not has_perm:
                    self.stdout.write('  - can_edit_content эрхгүй (Content Editor group-д нэмэх)')
                    
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('\n✗ Хэрэглэгч олдсонгүй!'))
            self.stdout.write('bayasaa68@gmail.com email-тэй хэрэглэгч үүсгэх хэрэгтэй.')
