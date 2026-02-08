#!/usr/bin/env python
"""Хаан банкны сөрөг зарлагын дүнг эерэг болгох"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import BankTransaction

# Хаан банкны сөрөг зарлага бүхий гүйлгээ олох
khan_negative_expenses = BankTransaction.objects.filter(
    bank_name='KHAN',
    expense_amount__lt=0
)

count = khan_negative_expenses.count()
print(f"🔧 Засах гүйлгээ: {count}")

if count > 0:
    updated = 0
    for tx in khan_negative_expenses:
        old_expense = tx.expense_amount
        tx.expense_amount = abs(tx.expense_amount)
        tx.save()
        updated += 1
        if updated % 10 == 0:
            print(f"  {updated}/{count} засагдсан...")
    
    print(f"✓ {updated} гүйлгээний зарлагын дүнг эерэг болголоо")
else:
    print("✓ Сөрөг зарлага байхгүй")

# Орлогын хувьд ч шалгах
khan_negative_income = BankTransaction.objects.filter(
    bank_name='KHAN',
    income_amount__lt=0
)

count2 = khan_negative_income.count()
if count2 > 0:
    print(f"\n🔧 Сөрөг орлого засах: {count2}")
    updated2 = 0
    for tx in khan_negative_income:
        tx.income_amount = abs(tx.income_amount)
        tx.save()
        updated2 += 1
    print(f"✓ {updated2} гүйлгээний орлогын дүнг эерэг болголоо")
