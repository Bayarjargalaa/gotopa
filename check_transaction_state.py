#!/usr/bin/env python
"""Гүйлгээний эсрэг данс буцсан эсэхийг шалгах"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import BankTransaction

tx = BankTransaction.objects.get(id=4974)

print(f"📊 Гүйлгээ #{tx.id}:")
print(f"  Огноо: {tx.transaction_date}")
print(f"  Тайлбар: {tx.description}")
print(f"  Зарлага: {tx.expense_amount:,.0f}₮")
print(f"  Эсрэг данс: {tx.offset_account.code if tx.offset_account else 'Хоосон'}")
print(f"  Журнал: {tx.accounting_entry.id if tx.accounting_entry else 'Хоосон'}")
print(f"  is_processed: {tx.is_processed}")

if not tx.offset_account and not tx.accounting_entry and not tx.is_processed:
    print("\n✅ Бүгд зөв буцаагдлаа!")
else:
    print("\n⚠️ Бүрэн буцаагүй:")
    if tx.offset_account:
        print(f"  - Эсрэг данс үлдсэн: {tx.offset_account.code}")
    if tx.accounting_entry:
        print(f"  - Журнал үлдсэн: {tx.accounting_entry.id}")
    if tx.is_processed:
        print(f"  - is_processed=True үлдсэн")
