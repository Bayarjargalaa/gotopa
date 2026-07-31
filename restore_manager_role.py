"""
student_80100560-г MANAGER роль болгох
(Одоо MANAGER = сургалтын менежер, админ эрхгүй)
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from django.contrib.auth.models import User

def main():
    print("=" * 70)
    print("🔧 student_80100560-г MANAGER роль болгох")
    print("=" * 70)
    print()
    
    try:
        user = User.objects.get(username='student_80100560')
        profile = user.profile
        
        print("📋 ӨМНӨХ ТӨЛӨВ:")
        print(f"   ├─ Роль: {profile.get_role_display()}")
        print(f"   ├─ is_admin: {profile.is_admin}")
        print()
        
        # Change role to MANAGER
        profile.role = 'MANAGER'
        profile.save()
        
        # Refresh
        user.refresh_from_db()
        profile.refresh_from_db()
        
        print("📋 ШИНЭ ТӨЛӨВ:")
        print(f"   ├─ Роль: {profile.get_role_display()}")
        print(f"   ├─ is_admin: {profile.is_admin}")
        print(f"   ├─ is_training_manager: {profile.is_training_manager}")
        print()
        
        print("=" * 70)
        print("✅ АМЖИЛТТАЙ!")
        print("=" * 70)
        print()
        print("📌 ОДОО ХАРАГДАХ ЦЭСҮҮД:")
        print("   ✓ Хувийн")
        print("      - Dashboard")
        print("      - Миний мэдээлэл")
        print()
        print("   ✓ Сургалт")
        print("      - Хичээлүүд")
        print("      - Ирц бүртгэх ⭐")
        print("      - Төлбөр")
        print("      - Сурагчид")
        print("      - Сурагч бүртгэх")
        print()
        print("❌ ХАРАГДАХГҮЙ:")
        print("   ✗ Санхүү")
        print("   ✗ Бараа материал")
        print("   ✗ Харилцагч")
        print("   ✗ Тайлан")
        print("   ✗ Удирдлага")
        print("   ✗ Багш нар / Багш бүртгэх (зөвхөн админ)")
        print()
        print("💡 MANAGER роль = Сургалтын менежер (ирц бүртгэгч)")
        print()
        
    except User.DoesNotExist:
        print("❌ Хэрэглэгч олдсонгүй!")

if __name__ == '__main__':
    main()
