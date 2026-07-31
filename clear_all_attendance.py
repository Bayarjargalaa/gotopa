#!/usr/bin/env python
"""
Бүх ирцийн өгөгдлийг устгах скрипт
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import Attendance, TeacherAttendance

def clear_all_attendance():
    """Бүх ирцийн өгөгдлийг устга"""
    
    print("\n" + "="*80)
    print("🗑️  БҮХ ИРЦИЙН ӨГӨГДӨЛ УСТГАХ")
    print("="*80)
    
    # Сурагчдын ирц
    student_count = Attendance.objects.count()
    print(f"\n📌 Сурагчдын ирц: {student_count} бүр")
    if student_count > 0:
        Attendance.objects.all().delete()
        print(f"   ✓ {student_count} сурагчдын ирц устгагдлаа")
    else:
        print("   - Сурагчдын ирц байхгүй")
    
    # Багшийн ирц
    teacher_count = TeacherAttendance.objects.count()
    print(f"\n📌 Багшийн ирц: {teacher_count} бүр")
    if teacher_count > 0:
        TeacherAttendance.objects.all().delete()
        print(f"   ✓ {teacher_count} багшийн ирц устгагдлаа")
    else:
        print("   - Багшийн ирц байхгүй")
    
    # Шалгалт
    final_student = Attendance.objects.count()
    final_teacher = TeacherAttendance.objects.count()
    print(f"\n✅ Завсарлага хийлээ:")
    print(f"   - Сурагчдын ирц: {final_student} бүр")
    print(f"   - Багшийн ирц: {final_teacher} бүр")
    print("\n" + "="*80)

if __name__ == '__main__':
    clear_all_attendance()
