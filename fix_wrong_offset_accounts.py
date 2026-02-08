#!/usr/bin/env python
"""Буруу эсрэг данс холбогдсон гүйлгээ шалгах"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import BankTransaction, ChartOfAccounts

print("="*80)
print(f"⚠️ БУРУУ ЭСРЭГ ДАНС ХОЛБОГДСОН ГҮЙЛГЭЭ")
print("="*80)

# Орлого (income > 0) боловч эсрэг данс 4xxx биш
bad_income = BankTransaction.objects.filter(
    income_amount__gt=0,
    offset_account__isnull=False
).exclude(offset_account__code__startswith='4')

print(f"\n💰 ОРЛОГО - 4xxx биш эсрэг данс: {bad_income.count()}")
for tx in bad_income[:5]:
    print(f"  {tx.id} | {tx.transaction_date} | {tx.offset_account.code} {tx.offset_account.name} | {tx.income_amount:,.0f}₮")

# Зарлага (expense > 0) боловч эсрэг данс 5xxx биш  
bad_expense = BankTransaction.objects.filter(
    expense_amount__gt=0,
    offset_account__isnull=False
).exclude(offset_account__code__startswith='5')

print(f"\n💸 ЗАРЛАГА - 5xxx биш эсрэг данс: {bad_expense.count()}")
for tx in bad_expense[:5]:
    print(f"  {tx.id} | {tx.transaction_date} | {tx.offset_account.code} {tx.offset_account.name} | {tx.expense_amount:,.0f}₮")

# Засах санал
print(f"\n📋 Эсрэг дансны код:")
print(f"  1xxx - Хөрөнгө (Касс, Банк, Авлага)")
print(f"  2xxx - Өр (Өглөг)")
print(f"  3xxx - Өмч")
print(f"  4xxx - Орлого (ОРЛОГО БҮХИЙ ГҮЙЛГЭЭНД АШИГЛАХ)")
print(f"  5xxx - Зардал (ЗАРЛАГА БҮХИЙ ГҮЙЛГЭЭНД АШИГЛАХ)")

print(f"\n💡 Буруу эсрэг данстай гүйлгээг хоосон болгох уу? (y/n)")
response = input("> ")

if response.lower() == 'y':
    count1 = bad_income.update(offset_account=None, is_processed=False)
    count2 = bad_expense.update(offset_account=None, is_processed=False)
    print(f"✓ {count1 + count2} гүйлгээний эсрэг данс хоослогдлоо. Дахин зөв данс холбоно уу.")
else:
    print("Болих")
