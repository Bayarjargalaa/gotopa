#!/usr/bin/env python
"""Банкны гүйлгээний статистик шалгах"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import BankTransaction

total = BankTransaction.objects.count()
unprocessed = BankTransaction.objects.filter(is_processed=False).count()
processed = BankTransaction.objects.filter(is_processed=True).count()

print("="*60)
print(f"📊 БАНКНЫ ГҮЙЛГЭЭНИЙ СТАТИСТИК")
print("="*60)
print(f"Нийт гүйлгээ: {total}")
print(f"⏳ Эсрэг данс холбоогүй: {unprocessed}")
print(f"✓ Журналд холбогдсон: {processed}")
print("="*60)

if total > 0:
    print("\n📋 Сүүлийн 5 гүйлгээ:")
    for tx in BankTransaction.objects.order_by('-transaction_date', '-id')[:5]:
        status = "✓ Журналд" if tx.is_processed else "⏳ Хүлээгдэж буй"
        offset = f"{tx.offset_account.code}" if tx.offset_account else "Хоосон"
        print(f"  {tx.transaction_date} | {tx.bank_account.code} | {offset} | {status}")
