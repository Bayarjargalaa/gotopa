from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from main.models import UserProfile, UserRole


class Command(BaseCommand):
    help = 'Content Editor эрхтэй жишээ хэрэглэгч үүсгэх'

    def handle(self, *args, **kwargs):
        username = 'content_editor'
        password = 'gotopa2025'
        
        # Хэрэглэгч үүсгэх
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': 'editor@gotopa.mn',
                'is_staff': True,  # Staff status олгох
                'is_active': True,
            }
        )
        
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Хэрэглэгч үүсгэлээ: {username}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'○ Хэрэглэгч аль хэдийн байна: {username}')
            )
        
        # UserProfile үүсгэх
        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'mongolian_name': 'Агуулга засагч',
                'role': UserRole.STUDENT,  # Role нь хамаагүй
                'phone': '+97699000001',
            }
        )
        
        if profile_created:
            self.stdout.write(
                self.style.SUCCESS(f'  + Профайл үүсгэлээ: {profile.mongolian_name}')
            )
        
        # Content Editor group-д нэмэх
        try:
            group = Group.objects.get(name='Content Editor')
            user.groups.add(group)
            self.stdout.write(
                self.style.SUCCESS(f'  + "Content Editor" бүлэгт нэмлээ')
            )
        except Group.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('  ✗ "Content Editor" бүлэг олдсонгүй!')
            )
            self.stdout.write(
                self.style.WARNING('    Эхлээд: python manage.py setup_content_editor')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Амжилттай! Нэвтрэх мэдээлэл:'
            )
        )
        self.stdout.write(f'   Username: {username}')
        self.stdout.write(f'   Password: {password}')
        self.stdout.write(f'   URL: http://127.0.0.1:8000/admin/')
