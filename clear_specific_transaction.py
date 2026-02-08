#!/usr/bin/env python
"""2025-12-29 дахь 64000₮ орлогын гүйлгээг хоослох"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import BankTransaction
from datetime import date

# 2025-12-29, 64000₮ орлого бүхий гүйлгээ хайх
target = BankTransaction.objects.filter(
    transaction_date=date(2025, 12, 29),
    income_amount=64000,
    description__icontains='ЁНДОНЖАМЦ'
).first()

if target:
    print(f"✓ Гүйлгээ олдлоо:")
    print(f"  ID: {target.id}")
    print(f"  Огноо: {target.transaction_date}")
    print(f"  Тайлбар: {target.description}")
    print(f"  Орлого: {target.income_amount:,.0f}₮")
    print(f"  Одоогийн эсрэг данс: {target.offset_account.code if target.offset_account else 'Хоосон'}")
    
    if target.offset_account:
        old_code = target.offset_account.code
        old_name = target.offset_account.name
        
        target.offset_account = None
        target.is_processed = False
        target.save()
        
        print(f"\n✓ Эсрэг данс хоослогдлоо:")
        print(f"  {old_code} - {old_name} → Хоосон")
        print(f"  Төлөв: is_processed = False")
    else:
        print(f"\n⚠️ Эсрэг данс аль хэдийн хоосон байна.")
else:
    print("✗ Гүйлгээ олдсонгүй.")
