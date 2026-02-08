#!/usr/bin/env python
"""Журналд холбогдоогүй гүйлгээнүүдийн allocation-уудыг шалгах"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import BankTransaction, PaymentAllocation

# Журналд холбогдоогүй гүйлгээнүүд
unprocessed = BankTransaction.objects.filter(is_processed=False)

# Тэдгээрт холбогдсон allocation-ууд
allocations = PaymentAllocation.objects.filter(transaction__in=unprocessed)

print("="*80)
print(f"📊 ЖУРНАЛД ХОЛБОГДООГҮЙ ГҮЙЛГЭЭНҮҮДИЙН ALLOCATION-УУД")
print("="*80)
print(f"Журналд холбогдоогүй гүйлгээ: {unprocessed.count()}")
print(f"Тэдгээрт холбогдсон төлбөрийн allocation: {allocations.count()}")
print("="*80)

if allocations.exists():
    print("\n📋 Жишээ allocation-ууд (эхний 15):")
    for a in allocations[:15]:
        student_name = a.student.mongolian_name if a.student else "Хоосон"
        course_name = a.course.name if a.course else "Хоосон"
        month_year = f"{a.year}/{a.month:02d}"
        print(f"  ID:{a.id:4d} | Гүйлгээ:{a.transaction_id:4d} | {student_name:20s} | {course_name:15s} | {a.amount:>10,.0f}₮ | {month_year}")
    
    print("\n" + "="*80)
    print("⚠️  ЭНЭ ALLOCATION-УУДЫГ УСТГАХ УУ?")
    print("   Эдгээр нь журналд холбогдоогүй гүйлгээнүүдтэй холбоотой учраас")
    print("   сурагчийн төлбөрийн хуудсан дээр буруу харагдаж байна.")
    print("="*80)
    
    answer = input("\nУстгах уу? (тийм/үгүй): ").strip().lower()
    
    if answer in ['тийм', 'y', 'yes']:
        count = allocations.count()
        allocations.delete()
        print(f"\n✅ {count} allocation амжилттай устгагдлаа!")
    else:
        print("\n❌ Цуцлагдлаа. Юу ч устгагдсангүй.")
else:
    print("\n✅ Журналд холбогдоогүй allocation байхгүй байна!")
