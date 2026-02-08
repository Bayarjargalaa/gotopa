#!/usr/bin/env python
"""Журналд холбогдоогүй allocation-уудыг устгах"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import BankTransaction, PaymentAllocation

# Журналд холбогдоогүй гүйлгээнүүд
unprocessed = BankTransaction.objects.filter(is_processed=False)

# Тэдгээрт холбогдсон allocation-ууд
allocations = PaymentAllocation.objects.filter(transaction__in=unprocessed)

count = allocations.count()

if count > 0:
    print(f"⚠️  {count} allocation устгах гэж байна...")
    
    for a in allocations:
        student_name = a.student.mongolian_name if a.student else "Хоосон"
        course_name = a.course.name if a.course else "Хоосон"
        month_year = f"{a.year}/{a.month:02d}"
        print(f"  Устгах: ID:{a.id} | Гүйлгээ:{a.transaction_id} | {student_name} | {course_name} | {a.amount:,.0f}₮ | {month_year}")
    
    # Устгах
    allocations.delete()
    print(f"\n✅ {count} allocation амжилттай устгагдлаа!")
else:
    print("✅ Устгах allocation байхгүй!")
