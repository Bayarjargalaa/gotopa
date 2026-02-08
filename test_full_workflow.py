#!/usr/bin/env python
"""Журналын бичилт үүсгэж тестлэх"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import BankTransaction, ChartOfAccounts
from main.import_bank_transactions import regenerate_accounting_entries
from django.contrib.auth.models import User

# Эсрэг данс холбоогүй гүйлгээ олох
unprocessed = BankTransaction.objects.filter(
    is_processed=False,
    offset_account__isnull=True
).first()

if not unprocessed:
    print("⚠️ Эсрэг данс холбоогүй гүйлгээ олдсонгүй.")
    exit()

print(f"📊 Гүйлгээ олдлоо:")
print(f"  ID: {unprocessed.id}")
print(f"  Огноо: {unprocessed.transaction_date}")
print(f"  Тайлбар: {unprocessed.description[:50]}")
print(f"  Орлого: {unprocessed.income_amount}")
print(f"  Зарлага: {unprocessed.expense_amount}")

# Эсрэг данс сонгох (орлого бол 4xxx, зарлага бол 5xxx)
if unprocessed.income_amount > 0:
    offset = ChartOfAccounts.objects.filter(code__startswith='4', is_active=True).first()
    print(f"\n💰 Орлого тул 4xxx данс сонголоо: {offset.code} - {offset.name}")
else:
    offset = ChartOfAccounts.objects.filter(code__startswith='5', is_active=True).first()
    print(f"\n💸 Зарлага тул 5xxx данс сонголоо: {offset.code} - {offset.name}")

if not offset:
    print("⚠️ Эсрэг данс олдсонгүй.")
    exit()

# Эсрэг данс холбох
unprocessed.offset_account = offset
unprocessed.save()

# Журналын бичилт үүсгэх
user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User.objects.first()

print(f"\n📝 Журналын бичилт үүсгэж байна...")
result = regenerate_accounting_entries([unprocessed], user)

if result > 0:
    unprocessed.refresh_from_db()
    print(f"\n✓ Журналын бичилт үүслээ:")
    print(f"  Журнал ID: {unprocessed.accounting_entry.id}")
    print(f"  Төлөв: {'Журналд холбогдсон' if unprocessed.is_processed else 'Холбогдоогүй'}")
    
    # Журнал устгах
    entry_id = unprocessed.accounting_entry.id
    print(f"\n🗑️ Журналын бичилт #{entry_id} устгаж байна...")
    unprocessed.accounting_entry.delete()
    
    # Дахин унших
    unprocessed.refresh_from_db()
    
    print(f"\n✅ Дүн:")
    print(f"  Төлөв: {'Журналд холбогдсон' if unprocessed.is_processed else 'Холбогдоогүй'}")
    print(f"  Журнал: {unprocessed.accounting_entry.id if unprocessed.accounting_entry else 'Хоосон'}")
    
    if not unprocessed.is_processed and not unprocessed.accounting_entry:
        print(f"\n✓ АМЖИЛТТАЙ! Банкны гүйлгээ буцаагдлаа.")
    else:
        print(f"\n✗ АЛДАА! Банкны гүйлгээ буцаагүй байна.")
else:
    print("✗ Журналын бичилт үүсгэж чадсангүй.")
