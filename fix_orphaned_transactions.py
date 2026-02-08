#!/usr/bin/env python
"""Журналд холбогдсон гэж харагдаж байгаа боловч accounting_entry хоосон гүйлгээ шалгах"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import BankTransaction, AccountingEntry

# is_processed=True боловч accounting_entry=NULL
orphaned = BankTransaction.objects.filter(is_processed=True, accounting_entry__isnull=True)

print("="*80)
print(f"⚠️ ЖУРНАЛГҮЙ БОЛОВЧ 'ЖУРНАЛД' ГЭСЭН ГҮЙЛГЭЭ")
print("="*80)
print(f"Нийт: {orphaned.count()}\n")

for tx in orphaned[:10]:
    print(f"ID: {tx.id}")
    print(f"  Огноо: {tx.transaction_date}")
    print(f"  Данс: {tx.bank_account.code if tx.bank_account else 'N/A'}")
    print(f"  Тайлбар: {tx.description[:50]}")
    print(f"  Орлого: {tx.income_amount:,.0f}₮" if tx.income_amount > 0 else f"  Зарлага: {tx.expense_amount:,.0f}₮")
    print(f"  Эсрэг данс: {tx.offset_account.code if tx.offset_account else 'Хоосон'}")
    print(f"  is_processed: {tx.is_processed}")
    print(f"  accounting_entry: {tx.accounting_entry}")
    print()

# Засварлах эсэх
if orphaned.count() > 0:
    print(f"\n🔧 {orphaned.count()} гүйлгээг буцаах уу? (y/n)")
    response = input("> ")
    
    if response.lower() == 'y':
        updated = orphaned.update(is_processed=False)
        print(f"✓ {updated} гүйлгээний төлөв буцаагдлаа.")
    else:
        print("Болих")
else:
    print("✓ Асуудалтай гүйлгээ байхгүй.")
