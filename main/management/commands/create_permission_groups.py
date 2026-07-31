"""
Эрхийн бүлгүүдийг үүсгэх команд
Ажиллуулах: python manage.py create_permission_groups
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from main.models import (
    Product, StockMovement, Counterparty, ChartOfAccounts, 
    AccountingEntry, BankTransaction, Course, Enrollment, PageContent
)

class Command(BaseCommand):
    help = 'Системийн эрхийн бүлгүүдийг үүсгэнэ'

    def handle(self, *args, **kwargs):
        # 1. Агуулахын менежер - бараа материал, хөдөлгөөн
        inventory_group, created = Group.objects.get_or_create(name='Агуулахын менежер')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ "Агуулахын менежер" бүлэг үүсгэлээ'))
        
        inventory_permissions = Permission.objects.filter(
            content_type__in=[
                ContentType.objects.get_for_model(Product),
                ContentType.objects.get_for_model(StockMovement),
                ContentType.objects.get_for_model(Counterparty),
            ]
        )
        inventory_group.permissions.set(inventory_permissions)
        self.stdout.write(f'  └─ {inventory_permissions.count()} эрх нэмлээ')

        # 2. Санхүүчин - нягтлан бодох бүртгэл
        accountant_group, created = Group.objects.get_or_create(name='Санхүүчин')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ "Санхүүчин" бүлэг үүсгэлээ'))
        
        accountant_permissions = Permission.objects.filter(
            content_type__in=[
                ContentType.objects.get_for_model(ChartOfAccounts),
                ContentType.objects.get_for_model(AccountingEntry),
                ContentType.objects.get_for_model(BankTransaction),
                ContentType.objects.get_for_model(Counterparty),
            ]
        )
        accountant_group.permissions.set(accountant_permissions)
        self.stdout.write(f'  └─ {accountant_permissions.count()} эрх нэмлээ')

        # 3. Сургалтын менежер - хичээл, элсэлт
        course_manager_group, created = Group.objects.get_or_create(name='Сургалтын менежер')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ "Сургалтын менежер" бүлэг үүсгэлээ'))
        
        course_permissions = Permission.objects.filter(
            content_type__in=[
                ContentType.objects.get_for_model(Course),
                ContentType.objects.get_for_model(Enrollment),
            ]
        )
        course_manager_group.permissions.set(course_permissions)
        self.stdout.write(f'  └─ {course_permissions.count()} эрх нэмлээ')

        # 4. Агуулга засварлагч - хуудасны агуулга
        content_editor_group, created = Group.objects.get_or_create(name='Content Editor')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ "Content Editor" бүлэг үүсгэлээ'))
        
        content_permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(PageContent)
        )
        content_editor_group.permissions.set(content_permissions)
        # Add custom permission
        try:
            custom_perm = Permission.objects.get(codename='can_edit_content', content_type=ContentType.objects.get_for_model(PageContent))
            content_editor_group.permissions.add(custom_perm)
        except Permission.DoesNotExist:
            self.stdout.write(self.style.WARNING('  ⚠ can_edit_content эрх олдсонгүй'))
        self.stdout.write(f'  └─ {content_editor_group.permissions.count()} эрх нэмлээ')

        # 5. Зөвхөн унших - бүх мэдээлэл харах, засварлахгүй
        viewer_group, created = Group.objects.get_or_create(name='Харагч')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ "Харагч" бүлэг үүсгэлээ'))
        
        view_permissions = Permission.objects.filter(codename__startswith='view_')
        viewer_group.permissions.set(view_permissions)
        self.stdout.write(f'  └─ {view_permissions.count()} эрх нэмлээ')

        self.stdout.write(self.style.SUCCESS('\n✅ Бүх эрхийн бүлгүүд бэлэн болсон!'))
        self.stdout.write('\nХэрэглэгчдэд эрх олгох:')
        self.stdout.write('  1. Django админ рүү нэвтрэх')
        self.stdout.write('  2. Authentication and Authorization > Users сонгох')
        self.stdout.write('  3. Хэрэглэгч засах')
        self.stdout.write('  4. "Бүлгүүд" хэсэгт шаардлагатай бүлгүүдийг нэмэх')
        self.stdout.write('  5. "Staff status" шалгах (админ панел руу нэвтрэхэд)')
