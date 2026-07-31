"""
Шинэ бүлэг үүсгэж HTML-с удирдаж үзэх
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from django.contrib.auth.models import Group, Permission, User
from main.menu_config import get_user_menu

def demo_html_permission():
    """HTML эрхийн удирдлага demo"""
    print("\n" + "="*80)
    print("HTML ЭРХИЙН УДИРДЛАГА - DEMO")
    print("="*80)
    
    # 1. "Харагч" бүлэг үүсгэх (зөвхөн тайлан үзэх эрхтэй)
    viewer_group, created = Group.objects.get_or_create(name='Харагч')
    
    if created:
        print("\n✓ 'Харагч' бүлэг шинээр үүссэн")
    else:
        print("\n✓ 'Харагч' бүлэг байсан, эрхүүдийг шинэчилнэ")
        viewer_group.permissions.clear()
    
    # Зөвхөн view эрхүүд өгөх
    view_perms = Permission.objects.filter(
        content_type__app_label='main',
        codename__startswith='view_'
    ).filter(
        content_type__model__in=['product', 'sale', 'purchase', 'stockmovement']
    )
    
    viewer_group.permissions.set(view_perms)
    print(f"   {view_perms.count()} view эрх нэмэгдлээ")
    
    # 2. Тест хэрэглэгч үүсгэх
    user, created = User.objects.get_or_create(
        username='demo_viewer',
        defaults={'first_name': 'Демо', 'last_name': 'Харагч'}
    )
    
    if created:
        user.set_password('demo123')
        user.save()
        print(f"\n✓ {user.username} хэрэглэгч үүссэн")
    else:
        print(f"\n✓ {user.username} хэрэглэгч байсан")
    
    # UserProfile шалгах
    from main.models import UserProfile, UserRole
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'role': UserRole.STUDENT,
            'mongolian_name': 'Демо Харагч'
        }
    )
    
    # 3. Бүлэгт оруулах
    user.groups.clear()
    user.groups.add(viewer_group)
    print(f"   '{viewer_group.name}' бүлэгт оруулсан")
    
    # 4. Цэс шалгах
    menu = get_user_menu(user)
    
    print(f"\n📋 {user.username} хэрэглэгчийн цэс ({len(menu)} бүлэг):")
    for section in menu:
        print(f"\n📁 {section['section']}")
        for item in section['items']:
            print(f"   ├─ {item['label']}")
    
    # 5. Зааварчилгаа
    print("\n" + "="*80)
    print("ДАРААХ АЛХМУУД:")
    print("="*80)
    print("""
1. Сервер ажиллуулах: python manage.py runserver

2. Админаар нэвтрэх: president / gotopa2025

3. Эрхийн бүлгүүд (HTML) хуудас руу орох

4. "Харагч" бүлгийг засах

5. Эрхүүд нэмэх/хасах (checkbox-ээр)

6. Хадгалах

7. demo_viewer нэвтрэх: demo_viewer / demo123

8. F5 дарж цэс харагдахыг шалгах!

ТАЙЛБАР:
- Одоо "Харагч" бүлэгт зөвхөн VIEW эрхүүд байна
- HTML дээрээс ADD/CHANGE/DELETE эрх нэмбэл цэс нэмэгдэнэ
- Эрх хасбал цэс алга болно
- Real-time ажиллана - F5 дарахад л болно!
    """)
    print("="*80 + "\n")

if __name__ == '__main__':
    demo_html_permission()
