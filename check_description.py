#!/usr/bin/env python
"""Банкны гүйлгээний тайлбар шалгах"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import BankTransaction

# "данс" гэсэн үг агуулсан гүйлгээнүүд
txs = BankTransaction.objects.filter(description__icontains='данс')[:10]
total = BankTransaction.objects.filter(description__icontains='данс').count()

print(f"\n{'='*80}")
print(f"'данс' гэсэн үг агуулсан банкны гүйлгээ: {total}")
print(f"{'='*80}\n")

if total == 0:
    print("⚠️ 'данс' гэсэн үг агуулсан гүйлгээ олдсонгүй.\n")
    
    # Нийт гүйлгээний тоо
    total_txs = BankTransaction.objects.count()
    print(f"Нийт банкны гүйлгээ: {total_txs}")
    
    if total_txs > 0:
        print("\nЭхний 5 гүйлгээний тайлбар:")
        for tx in BankTransaction.objects.all()[:5]:
            print(f"  - {tx.description[:100]}")
else:
    for tx in txs:
        print(f"ID: {tx.id}")
        print(f"  Огноо: {tx.transaction_date}")
        print(f"  Тайлбар: {tx.description}")
        print(f"  Дүн: {tx.income_amount if tx.income_amount > 0 else tx.expense_amount}")
        print()
