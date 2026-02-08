#!/usr/bin/env python
"""Журналын бичилт устгах үед банкны гүйлгээ буцах тестлэх"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import BankTransaction, AccountingEntry

# Журналд холбогдсон банкны гүйлгээ олох
processed = BankTransaction.objects.filter(is_processed=True, accounting_entry__isnull=False).first()

if processed:
    print(f"📊 Тест гүйлгээ олдлоо:")
    print(f"  ID: {processed.id}")
    print(f"  Огноо: {processed.transaction_date}")
    print(f"  Тайлбар: {processed.description[:50]}")
    print(f"  Төлөв: {'Журналд холбогдсон' if processed.is_processed else 'Холбогдоогүй'}")
    print(f"  Журнал ID: {processed.accounting_entry.id if processed.accounting_entry else 'Хоосон'}")
    
    entry_id = processed.accounting_entry.id
    
    # Журналын бичилт устгах
    print(f"\n🗑️ Журналын бичилт #{entry_id} устгаж байна...")
    processed.accounting_entry.delete()
    
    # Гүйлгээг дахин унших
    processed.refresh_from_db()
    
    print(f"\n✅ Дүн:")
    print(f"  Төлөв: {'Журналд холбогдсон' if processed.is_processed else 'Холбогдоогүй'}")
    print(f"  Журнал ID: {processed.accounting_entry.id if processed.accounting_entry else 'Хоосон'}")
    
    if not processed.is_processed and not processed.accounting_entry:
        print(f"\n✓ АМЖИЛТТАЙ! Банкны гүйлгээ буцаагдлаа.")
    else:
        print(f"\n✗ АЛДАА! Банкны гүйлгээ буцаагүй байна.")
else:
    print("⚠️ Журналд холбогдсон банкны гүйлгээ олдсонгүй. Эхлээд гүйлгээ холбоно уу.")
