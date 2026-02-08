#!/usr/bin/env python
"""Хаан банкны зарлагын дүн шалгах"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import BankTransaction

# Хаан банкны гүйлгээ
khan_transactions = BankTransaction.objects.filter(bank_name='KHAN').order_by('-transaction_date', '-id')[:10]

print("="*80)
print(f"🏦 ХААН БАНКНЫ ГҮЙЛГЭЭ (Сүүлийн 10)")
print("="*80)

for tx in khan_transactions:
    income = tx.income_amount or 0
    expense = tx.expense_amount or 0
    print(f"Огноо: {tx.transaction_date}")
    print(f"  Тайлбар: {tx.description[:50]}")
    print(f"  Орлого: {income:,.0f}₮")
    print(f"  Зарлага: {expense:,.0f}₮")
    print(f"  Данс: {tx.bank_account.code if tx.bank_account else 'N/A'}")
    print()

# Статистик
total_khan = BankTransaction.objects.filter(bank_name='KHAN').count()
khan_with_expense = BankTransaction.objects.filter(bank_name='KHAN', expense_amount__gt=0).count()
khan_with_income = BankTransaction.objects.filter(bank_name='KHAN', income_amount__gt=0).count()

print("="*80)
print(f"Нийт Хаан банкны гүйлгээ: {total_khan}")
print(f"Зарлага бүхий гүйлгээ: {khan_with_expense}")
print(f"Орлого бүхий гүйлгээ: {khan_with_income}")
print("="*80)
