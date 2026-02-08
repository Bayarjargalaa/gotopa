"""
Бүх хэрэглэгчдэд staff эрх өгөх команд
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Бүх хэрэглэгчдэд staff эрх өгөх'

    def handle(self, *args, **options):
        users = User.objects.all()
        count = 0
        
        for user in users:
            if not user.is_staff:
                user.is_staff = True
                user.save()
                count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {user.username} - staff эрх олголоо')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'○ {user.username} - аль хэдийн staff байна')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"="*60}\n'
                f'Нийт: {users.count()} хэрэглэгч\n'
                f'Staff эрх олгосон: {count}\n'
                f'{"="*60}'
            )
        )
