#!/usr/bin/env python
"""Буруу дансны кодуудыг засах"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import ChartOfAccounts

# 510101 Борлуулалтын орлого → 411001
# 510102 Үйлчилгээний орлого → 411002

fixes = [
    ('510101', '411001', 'Борлуулалтын орлого'),
    ('510102', '411002', 'Үйлчилгээний орлого'),
]

print("="*80)
print("🔧 ДАНСНЫ КОДУУДЫГ ЗАСАХ")
print("="*80)

for old_code, new_code, name in fixes:
    try:
        account = ChartOfAccounts.objects.get(code=old_code)
        print(f"\n✓ Олдлоо: {old_code} - {account.name}")
        print(f"  → Шинэ код: {new_code}")
        
        # Шинэ код давхцаж байгаа эсэхийг шалгах
        if ChartOfAccounts.objects.filter(code=new_code).exists():
            print(f"  ⚠️ {new_code} код аль хэдийн байна, алгасав.")
            continue
        
        account.code = new_code
        account.save()
        print(f"  ✓ Засагдлаа!")
        
    except ChartOfAccounts.DoesNotExist:
        print(f"\n✗ {old_code} олдсонгүй, алгасав.")

print("\n" + "="*80)
print("✓ Дууслаа")
print("="*80)
