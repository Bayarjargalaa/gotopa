"""Төлбөрийн харилцаа - Сурагчдын төлбөр, ирцийг он, сараар харуулах"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from datetime import datetime, date
from collections import defaultdict
from decimal import Decimal

from .models import (
    UserProfile, UserRole, Course, Enrollment, Attendance, BankTransaction
)


@login_required
def student_payments(request):
    """
    Сурагчдын төлбөр болон ирцийг он, сараар харуулах
    - Мөр: Сурагчид (анги ангиараа)
    - Баганы: Он, сар
    - Нүд: Төлбөр дүн + Ирц тоо
    """
    # Зөвхөн админ болон багш харна
    if not (request.user.profile.is_admin or request.user.profile.is_teacher):
        messages.error(request, 'Таньд энэ хуудас руу нэвтрэх эрх байхгүй.')
        return redirect('main:dashboard')
    
    # Он, сар шүүлт (query параметрээс)
    current_year = datetime.now().year
    selected_year = int(request.GET.get('year', current_year))
    selected_month = request.GET.get('month', 'all')  # 'all' эсвэл 1-12
    selected_course = request.GET.get('course', 'all')  # 'all' эсвэл course.id
    
    # Бүх курсууд
    courses = Course.objects.filter(is_active=True).order_by('level', 'name')
    
    # Он, сарын жагсаалт (dropdown-д харуулах)
    # Банкны гүйлгээнээс он-уудыг авах, хоосон бол өнөөгийн он харуулах
    payment_years = BankTransaction.objects.filter(
        income_type='STUDENT_PAYMENT'
    ).dates('transaction_date', 'year')
    
    if payment_years:
        min_year = payment_years[0].year
        max_year = max(current_year, payment_years[len(payment_years)-1].year)
        years = list(range(min_year, max_year + 2))
    else:
        years = list(range(2024, current_year + 2))
    
    months = [
        (1, '1-р сар'), (2, '2-р сар'), (3, '3-р сар'),
        (4, '4-р сар'), (5, '5-р сар'), (6, '6-р сар'),
        (7, '7-р сар'), (8, '8-р сар'), (9, '9-р сар'),
        (10, '10-р сар'), (11, '11-р сар'), (12, '12-р сар'),
    ]
    
    # Сурагчдыг анги (course)-аар бүлэглэх
    enrollments = Enrollment.objects.filter(
        is_active=True,
        status__in=['APPROVED', 'COMPLETED']
    ).select_related('student', 'course')
    
    # Курс шүүлт
    if selected_course != 'all':
        enrollments = enrollments.filter(course_id=selected_course)
    
    # Курс-оор бүлэглэх
    course_students = defaultdict(list)
    for enrollment in enrollments:
        course_students[enrollment.course].append(enrollment)
    
    # Харагдах сурагчдын ID-г цуглуулах (зөвхөн бүртгэлтэй сурагчид)
    visible_student_ids = set(enrollment.student_id for enrollment in enrollments)
    
    # Ирцийн мэдээлэл цуглуулах
    # Attendance -> Enrollment -> Student
    attendance_query = Attendance.objects.filter(
        present=True,
        date__year=selected_year
    ).select_related('enrollment__student')
    
    if selected_month != 'all':
        attendance_query = attendance_query.filter(date__month=int(selected_month))
    
    # {student_id: {month: attendance_count}}
    student_attendance = defaultdict(lambda: defaultdict(int))
    for attendance in attendance_query:
        student_id = attendance.enrollment.student_id
        month = attendance.date.month
        student_attendance[student_id][month] += 1
    
    # Хүснэгтэнд харуулах өгөгдөл бэлтгэх
    # [{course: course_obj, enrollments: [{enrollment, months_data: {...}}]}]
    table_data = []
    
    for course, course_enrollments in course_students.items():
        enrollment_rows = []
        course_total = Decimal(0)  # Анги бүрийн нийт дүн
        
        # ЗӨВХӨН энэ ангийн төлбөрүүдийг авах - PaymentAllocation-аас
        course_student_ids = [enr.student_id for enr in course_enrollments]
        from .models import PaymentAllocation
        course_payments_query = PaymentAllocation.objects.filter(
            student_id__in=course_student_ids,
            course=course,
            year=selected_year
        ).select_related('transaction', 'student', 'course')
        
        if selected_month != 'all':
            course_payments_query = course_payments_query.filter(month=int(selected_month))
        
        # Энэ ангийн төлбөрийн мэдээлэл цуглуулах
        # {student_id: {month: {'amount': total, 'transactions': [...]}}}
        course_student_payments = defaultdict(lambda: defaultdict(lambda: {'amount': Decimal(0), 'transactions': []}))
        for allocation in course_payments_query:
            student_id = allocation.student_id
            month = allocation.month
            course_student_payments[student_id][month]['amount'] += allocation.amount
            course_student_payments[student_id][month]['transactions'].append({
                'id': allocation.transaction_id,
                'amount': str(allocation.amount),
                'comment': allocation.comment or '',
                'color': allocation.color or '',
                'date': allocation.transaction.transaction_date.strftime('%Y-%m-%d')
            })
        
        for enrollment in course_enrollments:
            student = enrollment.student
            student_id = student.id
            
            # Сар бүрийн өгөгдөл
            months_data = {}
            student_total = Decimal(0)  # Сурагч бүрийн нийт дүн
            
            for month_num in range(1, 13):
                payment_data = course_student_payments.get(student_id, {}).get(month_num, {'amount': Decimal(0), 'transactions': []})
                attendance_count = student_attendance.get(student_id, {}).get(month_num, 0)
                
                months_data[month_num] = {
                    'payment': payment_data['amount'],
                    'attendance': attendance_count,
                    'transactions': payment_data['transactions'],
                }
                student_total += payment_data['amount']
            
            enrollment_rows.append({
                'enrollment': enrollment,
                'student': student,
                'months_data': months_data,
                'student_total': student_total,
            })
            course_total += student_total
        
        # Сар бүрийн нийт дүн тооцох (баганы нийт)
        column_totals = {}
        for month_num in range(1, 13):
            month_total = Decimal(0)
            for row in enrollment_rows:
                month_total += row['months_data'][month_num]['payment']
            column_totals[month_num] = month_total
        
        table_data.append({
            'course': course,
            'enrollments': enrollment_rows,
            'course_total': course_total,
            'column_totals': column_totals,
        })
    
    # Бүх хүснэгтийн нийт дүн
    grand_total = sum(course_data['course_total'] for course_data in table_data)
    
    # selected_month-ыг int болгох (template-д ашиглах)
    selected_month_int = int(selected_month) if selected_month != 'all' else None
    
    # Төлбөрийн статистик
    total_payments = sum(
        month_data['payment']
        for course_data in table_data
        for enr in course_data['enrollments']
        for month_data in enr['months_data'].values()
    )
    total_payments_count = len([
        p for p in BankTransaction.objects.filter(
            income_type='STUDENT_PAYMENT',
            income_year=selected_year
        )
    ])
    
    context = {
        'table_data': table_data,
        'years': years,
        'months': months,
        'courses': courses,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'selected_month_int': selected_month_int,
        'selected_course': selected_course,
        'total_payments': total_payments,
        'total_payments_count': total_payments_count,
        'grand_total': grand_total,
    }
    
    return render(request, 'main/student_payments.html', context)


@login_required
def update_payment_comment(request, transaction_id):
    """Төлбөрийн тэмдэглэл болон өнгө шинэчлэх (AJAX)"""
    import json
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST хүсэлт шаардлагатай'})
    
    try:
        # JSON өгөгдөл унших
        data = json.loads(request.body)
        comment = data.get('comment', '')
        color = data.get('color', '')
        
        # Transaction олох
        transaction = BankTransaction.objects.get(id=transaction_id)
        
        # Зөвхөн админ хэрэглэгч засах эрхтэй
        if not request.user.profile.is_admin:
            return JsonResponse({'success': False, 'error': 'Зөвхөн админ засах эрхтэй'})
        
        # Хадгалах
        transaction.payment_comment = comment
        transaction.payment_color = color
        transaction.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Тэмдэглэл амжилттай хадгалагдлаа'
        })
        
    except BankTransaction.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Төлбөрийн мэдээлэл олдсонгүй'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
