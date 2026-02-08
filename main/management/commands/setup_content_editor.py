from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from main.models import PageContent


class Command(BaseCommand):
    help = 'Content Editor бүлэг үүсгэж, хуудасны агуулга засах эрх олгох'

    def handle(self, *args, **kwargs):
        # Content Editor group үүсгэх
        group, created = Group.objects.get_or_create(name='Content Editor')
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('✓ "Content Editor" бүлэг үүсгэлээ')
            )
        else:
            self.stdout.write(
                self.style.WARNING('○ "Content Editor" бүлэг аль хэдийн байна')
            )
        
        # PageContent model-д хамаарах бүх эрхийг олох
        content_type = ContentType.objects.get_for_model(PageContent)
        permissions = Permission.objects.filter(content_type=content_type)
        
        # Эрхүүдийг group-д олгох
        for perm in permissions:
            group.permissions.add(perm)
            self.stdout.write(
                self.style.SUCCESS(f'  + Эрх нэмсэн: {perm.name}')
            )
        
        # Custom permission олгох
        try:
            can_edit = Permission.objects.get(
                codename='can_edit_content',
                content_type=content_type
            )
            group.permissions.add(can_edit)
            self.stdout.write(
                self.style.SUCCESS(f'  + Custom эрх нэмсэн: {can_edit.name}')
            )
        except Permission.DoesNotExist:
            self.stdout.write(
                self.style.WARNING('  ! Custom permission олдсонгүй (migration ажиллуулна уу)')
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Амжилттай дууслаа! '
                f'"{group.name}" бүлэгт {group.permissions.count()} эрх олголоо.'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                '\nХэрэглэгчдэд эрх олгохын тулд:'
            )
        )
        self.stdout.write('  1. Admin панел: /admin/')
        self.stdout.write('  2. Хэрэглэгчид -> Хэрэглэгч сонгох')
        self.stdout.write('  3. "Бүлгүүд" талбарт "Content Editor" нэмэх')
        self.stdout.write('  4. "Ажилтан статус" (Staff status) тэмдэглэх')
        self.stdout.write('  5. Хадгалах')
