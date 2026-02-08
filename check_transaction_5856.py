#!/usr/bin/env python
"""Гүйлгээ 5856-г шалгах"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import BankTransaction

bt = BankTransaction.objects.filter(id=5856).first()

if bt:
    print(f"ID: {bt.id}")
    print(f"Type: {bt.account_type}")
    print(f"Bank: {bt.bank_name}")
    print(f"Description: {bt.description}")
    print(f"Date: {bt.transaction_date}")
    print(f"Income: {bt.income_amount}")
    print(f"Expense: {bt.expense_amount}")
else:
    print("Гүйлгээ 5856 олдсонгүй!")
