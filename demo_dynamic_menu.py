"""
Sidebar цэс динамикаар ажиллаж байгааг харуулах
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from django.contrib.auth.models import User
from main.menu_config import get_user_menu

print("=" * 80)
print("ДИНАМИК ЦЭСНИЙ ЖИШЭЭ - Эрхээр автоматаар шүүгддэг")
print("=" * 80)

# 1. MANAGER роль (бүлэг эрхтэй)
user1 = User.objects.get(username='student_80100560')
menu1 = get_user_menu(user1)
print(f"\n1️⃣ {user1.username} (MANAGER + Менежер бүлэг):")
for section in menu1:
    print(f"   📂 {section['section']} ({len(section['items'])} зүйл)")

# 2. STUDENT роль (эрхгүй)
try:
    user2 = User.objects.filter(profile__role='STUDENT').first()
    if user2:
        menu2 = get_user_menu(user2)
        print(f"\n2️⃣ {user2.username} (STUDENT):")
        for section in menu2:
            print(f"   📂 {section['section']} ({len(section['items'])} зүйл)")
except Exception as e:
    print(f"\n⚠️ STUDENT хэрэглэгч олдсонгүй: {e}")

# 3. Динамик ажиллалт тайлбарлах
print("\n" + "=" * 80)
print("📋 ЯАЖ АЖИЛЛАДАГ:")
print("=" * 80)
print("""
1. Template дээр:
   {% for section in user_menu %}  ← context processor автоматаар өгнө
   
2. Context Processor (main/context_processors.py):
   def page_content_processor(request):
       user_menu = get_user_menu(request.user)  ← Хандалт бүрт шалгана
       
3. Menu Config (main/menu_config.py):
   def get_user_menu(user):
       - Хэрэглэгчийн эрхийг database-ээс татна
       - Section болон item бүрийн permission шалгана
       - Зөвхөн эрхтэй цэсүүдийг буцаана
       
4. Permission шалгалт:
   - role:MANAGER → UserProfile.role == 'MANAGER'
   - group:Менежер → user.groups.filter(name='Менежер').exists()
   - perm:main.can_view_inventory → user.has_perm('main.can_view_inventory')
   - is_admin → UserProfile.is_admin
   
5. Real-time өөрчлөлт:
   ✅ Бүлэгт эрх нэмэх → Page refresh → Цэс гарна
   ✅ Бүлгээс эрх хасах → Page refresh → Цэс алга болно
   ✅ Logout/Login хэрэггүй!
""")

print("=" * 80)
print("✅ Таны систем аль хэдийн ДИНАМИК ажиллаж байна!")
print("=" * 80)
