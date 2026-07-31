"""
Enrollment харах эрхийг Менежер бүлэгт нэмэх скрипт
"""
import os
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from main.models import Enrollment

def setup_enrollment_permissions():
    """Enrollment-тай холбоотой permission-ууд үүсгэж, Менежер бүлэгт нэмэх"""
    
    # Менежер бүлэг авах эсвэл үүсгэх
    manager_group, created = Group.objects.get_or_create(name='Менежер')
    if created:
        print("✓ 'Менежер' бүлэг үүсгэгдлээ")
    else:
        print("✓ 'Менежер' бүлэг байгаа")
    
    # Enrollment content type
    enrollment_ct = ContentType.objects.get_for_model(Enrollment)
    
    # Enrollment харах эрх
    view_perm, created = Permission.objects.get_or_create(
        codename='view_enrollment',
        content_type=enrollment_ct,
        defaults={'name': 'Can view enrollment'}
    )
    if created:
        print("✓ 'view_enrollment' эрх үүсгэгдлээ")
    else:
        print("✓ 'view_enrollment' эрх байгаа")
    
    # Enrollment өөрчлөх эрх
    change_perm, created = Permission.objects.get_or_create(
        codename='change_enrollment',
        content_type=enrollment_ct,
        defaults={'name': 'Can change enrollment'}
    )
    if created:
        print("✓ 'change_enrollment' эрх үүсгэгдлээ")
    else:
        print("✓ 'change_enrollment' эрх байгаа")
    
    # Менежер бүлэгт эрх нэмэх
    manager_group.permissions.add(view_perm, change_perm)
    print("\n✅ Менежер бүлэгт дараах эрхүүд нэмэгдлээ:")
    print("   - Enrollment харах")
    print("   - Enrollment баталгаажуулах/өөрчлөх")
    
    # Одоогийн бүлгийн эрхүүдийг харуулах
    print(f"\n📋 'Менежер' бүлгийн нийт эрхүүд: {manager_group.permissions.count()}")
    
    return manager_group

if __name__ == '__main__':
    print("=" * 60)
    print("Enrollment эрхийн тохиргоо эхэллээ...")
    print("=" * 60)
    
    manager_group = setup_enrollment_permissions()
    
    print("\n" + "=" * 60)
    print("✅ Бүх тохиргоо амжилттай хийгдлээ!")
    print("=" * 60)
    print("\n💡 Дараах зүйлсийг хийнэ үү:")
    print("   1. Менежер хэрэглэгчдийг 'Менежер' бүлэгт нэмнэ")
    print("   2. Сервер дахин ачаална (Ctrl+C дараад 'python manage.py runserver')")
    print("   3. Менежер нэвтэрч, 'Удирдлага > Бүртгэлүүд' цэсийг шалгана")
    print()
