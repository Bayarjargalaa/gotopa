#!/usr/bin/env python
"""Буруу эсрэг данс автоматаар хоослох"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import BankTransaction

# Зарлага боловч эсрэг данс 5xxx биш
bad_expense = BankTransaction.objects.filter(
    expense_amount__gt=0,
    offset_account__isnull=False
).exclude(offset_account__code__startswith='5')

print(f"Буруу эсрэг данстай зарлагын гүйлгээ: {bad_expense.count()}")
for tx in bad_expense:
    print(f"  {tx.id} | {tx.offset_account.code} → Хоослогдож байна")

count = bad_expense.update(offset_account=None, is_processed=False)
print(f"✓ {count} гүйлгээг хоослоо")
