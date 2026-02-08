#!/usr/bin/env python
"""Журналгүй боловч эсрэг данс үлдсэн гүйлгээг хоослох"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import BankTransaction

# accounting_entry байхгүй боловч offset_account байгаа
orphaned_offset = BankTransaction.objects.filter(
    accounting_entry__isnull=True,
    offset_account__isnull=False
)

print("="*80)
print("⚠️ ЖУРНАЛГҮЙ БОЛОВЧ ЭСРЭГ ДАНС ҮЛДСЭН ГҮЙЛГЭЭ")
print("="*80)
print(f"Нийт: {orphaned_offset.count()}\n")

for tx in orphaned_offset:
    print(f"ID: {tx.id} | {tx.transaction_date}")
    print(f"  Данс: {tx.bank_account.code if tx.bank_account else 'N/A'}")
    print(f"  Тайлбар: {tx.description[:50]}")
    print(f"  Эсрэг данс: {tx.offset_account.code} - {tx.offset_account.name}")
    print(f"  is_processed: {tx.is_processed}")
    print()

if orphaned_offset.count() > 0:
    count = orphaned_offset.update(offset_account=None, is_processed=False)
    print(f"✓ {count} гүйлгээний эсрэг данс хоослогдлоо.")
else:
    print("✓ Асуудалтай гүйлгээ байхгүй.")
