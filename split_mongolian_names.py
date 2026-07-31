"""
Mongolian_name-ыг овог, нэр болгон хуваах скрипт
Монголын нэрний формат: "Овог Нэр" (жишээ: "Батаа Дорж")
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import UserProfile

def split_mongolian_names():
    """Mongolian_name-ыг овог, нэр болгон хуваах"""
    
    print("\n" + "="*80)
    print("🔄 МОНГОЛ НЭРИЙГ ОВОГ, НЭР БОЛГОН ХУВААХ")
    print("="*80)
    
    profiles = UserProfile.objects.all()
    total = profiles.count()
    updated = 0
    skipped = 0
    
    print(f"\n📊 Нийт {total} хэрэглэгч олдлоо")
    
    for profile in profiles:
        # Аль хэдийн овог, нэр байвал алгасах
        if profile.last_name and profile.first_name:
            print(f"   ⏭️  {profile.user.username}: Овог нэр аль хэдийн байна")
            skipped += 1
            continue
        
        # Mongolian_name байхгүй бол алгасах
        if not profile.mongolian_name:
            print(f"   ⚠️  {profile.user.username}: Mongolian_name хоосон")
            skipped += 1
            continue
        
        # Нэрийг хуваах
        name_parts = profile.mongolian_name.strip().split(maxsplit=1)
        
        if len(name_parts) == 2:
            # "Овог Нэр" формат
            profile.last_name = name_parts[0]
            profile.first_name = name_parts[1]
            profile.save()
            print(f"   ✅ {profile.user.username}: '{profile.mongolian_name}' → Овог: '{profile.last_name}', Нэр: '{profile.first_name}'")
            updated += 1
        elif len(name_parts) == 1:
            # Зөвхөн 1 үг байвал нэр гэж үзнэ
            profile.first_name = name_parts[0]
            profile.save()
            print(f"   ⚠️  {profile.user.username}: '{profile.mongolian_name}' → Нэр: '{profile.first_name}' (Овог байхгүй)")
            updated += 1
        else:
            # 3+ үг байвал эхнийг овог, үлдсэнийг нэр гэж үзнэ
            profile.last_name = name_parts[0]
            profile.first_name = ' '.join(name_parts[1:])
            profile.save()
            print(f"   ✅ {profile.user.username}: '{profile.mongolian_name}' → Овог: '{profile.last_name}', Нэр: '{profile.first_name}'")
            updated += 1
    
    print(f"\n{'='*80}")
    print(f"📊 ДҮГНЭЛТ:")
    print(f"   Нийт: {total}")
    print(f"   Шинэчлэгдсэн: {updated}")
    print(f"   Алгасав: {skipped}")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    split_mongolian_names()
