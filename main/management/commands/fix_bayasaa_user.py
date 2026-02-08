from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    help = 'bayasaa68@gmail.com хэрэглэгчид Content Editor эрх олгох'

    def handle(self, *args, **kwargs):
        email = 'bayasaa68@gmail.com'
        
        try:
            user = User.objects.get(email=email)
            self.stdout.write(self.style.SUCCESS(f'✓ Хэрэглэгч олдлоо: {user.username}'))
            
            # Одоогийн төлөв харуулах
            self.stdout.write(f'\n📊 Одоогийн төлөв:')
            self.stdout.write(f'  Email: {user.email}')
            self.stdout.write(f'  is_staff: {user.is_staff}')
            self.stdout.write(f'  is_superuser: {user.is_superuser}')
            self.stdout.write(f'  is_active: {user.is_active}')
            self.stdout.write(f'  Бүлгүүд: {[g.name for g in user.groups.all()]}')
            
            # Staff status олгох
            if not user.is_staff:
                self.stdout.write(self.style.WARNING('\n⚠ Staff status байхгүй байна...'))
                user.is_staff = True
                user.save()
                self.stdout.write(self.style.SUCCESS('✓ Staff status олгосон'))
            
            # Content Editor бүлэгт нэмэх
            try:
                group = Group.objects.get(name='Content Editor')
                if not user.groups.filter(name='Content Editor').exists():
                    self.stdout.write(self.style.WARNING('\n⚠ Content Editor бүлэгт байхгүй байна...'))
                    user.groups.add(group)
                    self.stdout.write(self.style.SUCCESS('✓ Content Editor бүлэгт нэмлээ'))
                else:
                    self.stdout.write(self.style.SUCCESS('\n✓ Content Editor бүлэгт аль хэдийн байна'))
            except Group.DoesNotExist:
                self.stdout.write(self.style.ERROR('\n✗ Content Editor бүлэг байхгүй байна'))
                self.stdout.write(self.style.WARNING('  python manage.py setup_content_editor командыг ажиллуулна уу'))
                return
            
            # Дүгнэлт
            can_edit = user.is_staff and (user.is_superuser or user.groups.filter(name='Content Editor').exists())
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Бүх тохиргоо хийгдлээ!'))
            self.stdout.write(self.style.SUCCESS(f'  {user.username} ({user.email}) АГУУЛГА ЗАСАХ ЭРХТЭЙ.'))
            self.stdout.write(f'\n📝 Нэвтрэх мэдээлэл:')
            self.stdout.write(f'  Email: {user.email}')
            self.stdout.write(f'  Username: {user.username}')
            self.stdout.write(f'  URL: http://127.0.0.1:8000/')
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ {email} email-тэй хэрэглэгч олдсонгүй'))
            self.stdout.write(self.style.WARNING(f'\nӨөр email эсвэл username ашиглана уу:'))
            self.stdout.write('  python manage.py shell')
            self.stdout.write('  >>> from django.contrib.auth.models import User')
            self.stdout.write('  >>> User.objects.all().values_list("username", "email")')
