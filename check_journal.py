#!/usr/bin/env python
"""Журналын бичилт шалгах"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import AccountingEntry

entries = AccountingEntry.objects.all().order_by('-entry_date', '-id')[:10]

print("="*80)
print(f"📊 ЖУРНАЛЫН БИЧИЛТ (Сүүлийн 10)")
print("="*80)
print(f"Нийт: {AccountingEntry.objects.count()}\n")

for entry in entries:
    print(f"ID: {entry.id} | {entry.entry_number}")
    print(f"  Огноо: {entry.entry_date}")
    print(f"  Дебит: {entry.debit_account.code if entry.debit_account else 'N/A'} - {entry.debit_amount:,.0f}₮")
    print(f"  Кредит: {entry.credit_account.code if entry.credit_account else 'N/A'} - {entry.credit_amount:,.0f}₮")
    print(f"  Тайлбар: {entry.description[:50]}")
    print()
