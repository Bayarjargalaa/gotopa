"""Төлбөрийн харилцаа - Сурагчдын төлбөр, ирцийг он, сараар харуулах"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from datetime import datetime, date
from collections import defaultdict
from decimal import Decimal

from .models import (
    UserProfile, UserRole, Course, Enrollment, Attendance, BankTransaction, PendingPayment,
    PaymentCellNote, PaymentDiscount,
)
from .books_period import get_books_start_date

# Хөнгөлөлтийн бэлэн загварууд: (нэр, төрөл, хэмжээ)
DISCOUNT_PRESETS = [
    ('Эхний сар үнэгүй', 'PERCENT', 100),
    ('Дахин элссэн хөнгөлөлт', 'PERCENT', 50),
    ('Ах дүүсийн хөнгөлөлт', 'PERCENT', 10),
]


def _can_mark_payments(user):
    """Төлбөр тэмдэглэх/засах эрх: админ, нягтлан, Менежер эсвэл банкны гүйлгээ засах эрхтэй."""
    profile = user.profile
    return (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.change_banktransaction')
    )


@login_required
def student_payments(request):
    """
    Сурагчдын төлбөр болон ирцийг он, сараар харуулах
    - Мөр: Сурагчид (анги ангиараа)
    - Баганы: Он, сар
    - Нүд: Төлбөр дүн + Ирц тоо
    """
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан бодогч, багш, Менежер бүлэг эсвэл төлбөр харах эрхтэй
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        profile.is_teacher or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.view_banktransaction')
    )
    
    if not has_access:
        messages.error(request, 'Таньд энэ хуудас руу нэвтрэх эрх байхгүй.')
        return redirect('main:dashboard')
    
    # Он, сар шүүлт (query параметрээс)
    current_year = datetime.now().year
    selected_year = int(request.GET.get('year', current_year))
    selected_month = request.GET.get('month', 'all')  # 'all' эсвэл 1-12
    selected_course = request.GET.get('course', 'all')  # 'all' эсвэл course.id
    # Бүртгэлийн төлөв: анхдагч нь зөвхөн баталсан
    status_choices = Enrollment.STATUS_CHOICES
    selected_status = request.GET.get('status', 'APPROVED')
    if selected_status != 'all' and selected_status not in dict(status_choices):
        selected_status = 'APPROVED'

    # Бүх курсууд
    courses = Course.objects.filter(is_active=True).order_by('level', 'name')
    
    # Он, сарын жагсаалт (dropdown-д харуулах)
    # Төлбөрийн мэдээлэл аль нэг таблаас ирж болно: PaymentAllocation.year, BankTransaction.income_year
    from .models import PaymentAllocation

    alloc_years_qs = PaymentAllocation.objects.values_list('year', flat=True).distinct()
    alloc_years = [int(y) for y in alloc_years_qs if y]

    tx_years_qs = BankTransaction.objects.filter(income_year__isnull=False).values_list('income_year', flat=True).distinct()
    tx_years = [int(y) for y in tx_years_qs if y]

    pending_years = set(PendingPayment.objects.values_list('year', flat=True).distinct())

    year_set = set(alloc_years) | set(tx_years) | pending_years
    if year_set:
        min_year = min(year_set)
        max_year = max(max(year_set), current_year)
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
    enrollments = Enrollment.objects.select_related('student__user', 'course').order_by(
        'course__level',
        'course__name',
        'student__first_name',
        'student__last_name',
        'student__mongolian_name',
        'student__user__username'
    )
    
    # Төлөв шүүлт
    if selected_status != 'all':
        enrollments = enrollments.filter(status=selected_status)

    # Курс шүүлт
    if selected_course != 'all':
        enrollments = enrollments.filter(course_id=selected_course)
    
    # Курс-оор бүлэглэх
    course_students = defaultdict(list)
    for enrollment in enrollments:
        course_students[enrollment.course].append(enrollment)

    # Анги бүрийн дотор сурагчдыг нэр (дараа нь овог)-оор эрэмбэлэх
    for course_enrollments in course_students.values():
        course_enrollments.sort(key=lambda e: e.student.name_first_display.lower())
    
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
    
    # {enrollment_id: {month: attendance_count}} — анги тус бүрийн ирц
    enrollment_attendance = defaultdict(lambda: defaultdict(int))
    for attendance in attendance_query:
        enrollment_attendance[attendance.enrollment_id][attendance.date.month] += 1
    
    # Хүснэгтэнд харуулах өгөгдөл бэлтгэх
    # [{course: course_obj, enrollments: [{enrollment, months_data: {...}}]}]
    table_data = []
    books_start = get_books_start_date()
    # Систем эхэлсэн сараас өмнөх сарын өрийг тооцохгүй (эхэлсэн сар өөрөө тооцогдоно)
    pre_start_months = {
        m for m in range(1, 13) if books_start and (selected_year, m) < (books_start.year, books_start.month)
    }

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
        ).select_related('transaction', 'student', 'course', 'pending_payment')
        
        if selected_month != 'all':
            course_payments_query = course_payments_query.filter(month=int(selected_month))

        # Нүдний тэмдэглэл, өнгө: {(student_id, month): {...}}
        course_notes = {
            (note.student_id, note.month): {'comment': note.comment, 'color': note.color}
            for note in PaymentCellNote.objects.filter(
                student_id__in=course_student_ids, course=course, year=selected_year
            )
        }

        # Хуулга хүлээж буй (банкны гүйлгээтэй холбогдоогүй) тэмдэглэлүүд
        # {student_id: {month: [pending, ...]}}
        course_pending = defaultdict(lambda: defaultdict(list))
        course_pre_start = []
        for pending in PendingPayment.objects.filter(
            student_id__in=course_student_ids, course=course, year=selected_year, allocation__isnull=True
        ):
            if pending.pre_start:
                course_pre_start.append(pending)
                continue
            course_pending[pending.student_id][pending.month].append({
                'id': pending.id,
                'amount': str(pending.amount),
                'paid_date': pending.paid_date.strftime('%Y-%m-%d'),
                'method': pending.get_method_display(),
                'payer_name': pending.payer_name,
                'comment': pending.comment,
            })
        
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
                'date': allocation.transaction.transaction_date.strftime('%Y-%m-%d'),
                'is_cash': allocation.transaction.account_type == 'CASH',
                'pre_marked': (
                    allocation.pending_payment.paid_date.strftime('%Y-%m-%d')
                    if hasattr(allocation, 'pending_payment') else ''
                ),
            })
        # Систем эхлэхээс өмнө бэлнээр төлсөн (журналгүй) — төлсөн дүнд тооцно
        for pending in course_pre_start:
            if selected_month != 'all' and pending.month != int(selected_month):
                continue
            cell = course_student_payments[pending.student_id][pending.month]
            cell['amount'] += pending.amount
            cell['transactions'].append({
                'id': None,
                'amount': str(pending.amount),
                'comment': pending.comment,
                'color': '',
                'date': pending.paid_date.strftime('%Y-%m-%d'),
                'is_cash': True,
                'pre_marked': '',
                'pre_start_id': pending.id,
            })
        
        # Хөнгөлөлтүүд: {(student_id, month): PaymentDiscount}
        course_discounts = {
            (d.student_id, d.month): d
            for d in PaymentDiscount.objects.filter(
                student_id__in=course_student_ids, course=course, year=selected_year
            )
        }

        fee = course.monthly_fee or Decimal('0')
        for enrollment in course_enrollments:
            student = enrollment.student
            student_id = student.id

            # Сар бүрийн өгөгдөл + төлөв
            months_data = {}
            student_total = Decimal(0)  # Сурагч бүрийн нийт дүн
            attendance_total = 0
            debt = Decimal(0)           # Ирсэн сарын дутуу төлбөрийн нийлбэр
            flags = set()
            visible_months = range(1, 13) if selected_month == 'all' else [int(selected_month)]
            filter_months = [m for m in visible_months if m not in pre_start_months]

            for month_num in range(1, 13):
                payment_data = course_student_payments.get(student_id, {}).get(month_num, {'amount': Decimal(0), 'transactions': []})
                attendance_count = enrollment_attendance.get(enrollment.id, {}).get(month_num, 0)
                paid = payment_data['amount']
                pending_list = course_pending.get(student_id, {}).get(month_num, [])
                pending_amount = sum((Decimal(p['amount']) for p in pending_list), Decimal(0))
                # Төлөв, өрийг хуулга хүлээж буй дүнг оролцуулж тооцно;
                # "Төлсөн" нийлбэрт зөвхөн банкаар баталгаажсан дүн орно.
                covered = paid + pending_amount
                discount = course_discounts.get((student_id, month_num))
                discount_amount = discount.amount_for(fee) if discount else Decimal(0)
                due = fee - discount_amount    # хөнгөлөлтийн дараах сарын төлбөр

                if discount and due <= 0 and covered <= 0:
                    state = 'discounted'       # бүрэн хөнгөлөлттэй (ж: эхний сар үнэгүй)
                elif covered <= 0 and attendance_count > 0:
                    state = 'unpaid'           # ирсэн ч төлөөгүй
                elif covered > 0 and due > 0 and covered < due:
                    state = 'partial'          # дутуу төлсөн
                elif pending_amount > 0:
                    state = 'pending'          # төлсөн гэж тэмдэглэсэн, хуулга хүлээж буй
                elif paid > 0:
                    state = 'paid'             # бүрэн төлсөн
                elif discount:
                    state = 'discounted'
                else:
                    state = 'empty'
                # Систем эхлэхээс өмнөх сард өр тооцохгүй
                if state in ('unpaid', 'partial') and month_num in pre_start_months:
                    state = 'pre_start'
                no_attendance = covered > 0 and attendance_count == 0
                # Төлсөн огноонууд (баталгаажсан + хуулга хүлээж буй)
                paid_dates = sorted({tx['date'] for tx in payment_data['transactions']} |
                                    {p['paid_date'] for p in pending_list})

                months_data[month_num] = {
                    'payment': paid,
                    'attendance': attendance_count,
                    'transactions': payment_data['transactions'],
                    'pending': pending_list,
                    'pending_amount': pending_amount,
                    'note': course_notes.get((student_id, month_num), {'comment': '', 'color': ''}),
                    'state': state,
                    'no_attendance': no_attendance,
                    'shortfall': (due - covered) if state == 'partial' else (due if state == 'unpaid' else Decimal(0)),
                    'due': due,
                    'paid_dates': paid_dates,
                    # Нүдэнд: сүүлийн огноо (ММ/ӨӨ), олон бол "+N"
                    'paid_date_label': (
                        paid_dates[-1][5:].replace('-', '/') +
                        (f' +{len(paid_dates) - 1}' if len(paid_dates) > 1 else '')
                    ) if paid_dates else '',
                    'discount': {
                        'name': discount.name,
                        'kind': discount.kind,
                        'value': f'{discount.value:f}',
                        'label': discount.label,
                        'amount': f'{discount_amount:.0f}',
                        'comment': discount.comment,
                    } if discount else None,
                }
                student_total += paid

                if month_num in visible_months:
                    attendance_total += attendance_count
                # Нөхцлийн шүүлтүүд систем эхэлсэн сараас өмнөхийг харахгүй
                if month_num in filter_months:
                    if state in ('unpaid', 'partial'):
                        flags.add(state)
                        debt += months_data[month_num]['shortfall']
                    if no_attendance:
                        flags.add('no_attendance')
                    if pending_list:
                        flags.add('pending')
                    if discount:
                        flags.add('discounted')
                    if months_data[month_num]['note']['comment']:
                        flags.add('noted')

            visible_paid = sum((months_data[m]['payment'] for m in visible_months), Decimal(0))
            filter_paid = sum((months_data[m]['payment'] for m in filter_months), Decimal(0))
            filter_pending = sum((months_data[m]['pending_amount'] for m in filter_months), Decimal(0))
            filter_attendance = sum(months_data[m]['attendance'] for m in filter_months)
            if filter_paid > 0 and not flags & {'unpaid', 'partial', 'pending'}:
                flags.add('paid_ok')
            if filter_paid + filter_pending <= 0:
                flags.add('never_paid')
            if filter_attendance == 0:
                flags.add('never_attended')

            notes_text = ' '.join(
                months_data[m]['note']['comment'] for m in visible_months if months_data[m]['note']['comment']
            )

            enrollment_rows.append({
                'enrollment': enrollment,
                'notes_text': notes_text,
                'student': student,
                'months_data': months_data,
                'student_total': student_total,
                'visible_paid': visible_paid,
                'attendance_total': attendance_total,
                'debt': debt,
                'flags': ' '.join(sorted(flags)),
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
            'fee': fee,
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
    # Тухайн оны сурагчийн төлбөрийн гүйлгээний тоо (хуваарилалтаас)
    total_payments_count = PaymentAllocation.objects.filter(year=selected_year).values('transaction_id').distinct().count()
    
    context = {
        'table_data': table_data,
        'years': years,
        'months': months,
        'courses': courses,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'selected_month_int': selected_month_int,
        'selected_course': selected_course,
        'status_choices': status_choices,
        'selected_status': selected_status,
        'total_payments': total_payments,
        'total_payments_count': total_payments_count,
        'grand_total': grand_total,
        'current_month': datetime.now().month if selected_year == datetime.now().year else 12,
        'can_mark_payments': _can_mark_payments(user),
        'cash_accounts': [{'id': a.id, 'label': f'{a.code} - {a.name}'} for a in _cash_accounts()],
        'today': date.today().strftime('%Y-%m-%d'),
        'books_start': books_start,
        'discount_presets': _discount_presets(),
    }
    
    return render(request, 'main/student_payments.html', context)


def _discount_presets():
    """Бэлэн загварууд + өмнө нь ашигласан хөнгөлөлтүүд (давхардалгүй)."""
    presets = [{'name': n, 'kind': k, 'value': str(v)} for n, k, v in DISCOUNT_PRESETS]
    seen = {p['name'] for p in presets}
    used = (PaymentDiscount.objects.values('name', 'kind', 'value')
            .annotate(n=Count('id')).order_by('-n')[:10])
    for d in used:
        if d['name'] not in seen:
            seen.add(d['name'])
            presets.append({'name': d['name'], 'kind': d['kind'], 'value': f"{d['value']:f}".rstrip('0').rstrip('.')})
    return presets


def _cash_accounts():
    """Кассын дансууд (100x, 101x)."""
    from .models import ChartOfAccounts
    return ChartOfAccounts.objects.filter(
        Q(code__startswith='100') | Q(code__startswith='101'), is_active=True
    ).order_by('code')


def _record_cash_payment(user, student, course, year, month, amount, paid_date, payer_name, cash_account_id=None):
    """Бэлнээр (касс) авсан төлбөрийг кассын орлого + хуваарилалт + журналаар шууд бүртгэнэ.

    Returns: алдааны текст эсвэл None.
    """
    from django.db import transaction as db_transaction
    from .models import ChartOfAccounts, CashFlowIndicator, PaymentAllocation
    from .bank_link_suggestions import FIXED_TYPE_DEFAULTS
    from .books_period import is_archived_date, can_view_archive
    from .import_bank_transactions import regenerate_accounting_entries

    if is_archived_date(paid_date) and not can_view_archive(user):
        # Систем эхлэхээс өмнөх төлбөр: касс, журналд бичихгүй, зөвхөн төлсөн гэж тэмдэглэнэ
        PendingPayment.objects.create(
            student=student, course=course, year=year, month=month, amount=amount,
            paid_date=paid_date, method='CASH', payer_name=payer_name, pre_start=True, created_by=user,
        )
        return None

    cash_accounts = _cash_accounts()
    cash_account = cash_accounts.filter(id=cash_account_id).first() if cash_account_id else cash_accounts.first()
    if not cash_account:
        return 'Кассын данс (100x/101x) олдсонгүй.'

    account_code, indicator_code = FIXED_TYPE_DEFAULTS['STUDENT_PAYMENT']
    offset_account = ChartOfAccounts.objects.filter(code=account_code).first()
    indicator = CashFlowIndicator.objects.filter(code=indicator_code).first()

    description = f'{student.name_first_display} - {course.name} {year}/{month:02d} сарын төлбөр (бэлэн)'
    if payer_name:
        description += f', төлсөн: {payer_name}'

    with db_transaction.atomic():
        tx = BankTransaction.objects.create(
            account_type='CASH',
            bank_name='CASH_REGISTER',
            bank_account=cash_account,
            transaction_date=paid_date,
            income_amount=amount,
            description=description,
            counterparty_name=payer_name,
            offset_account=offset_account,
            cash_flow_indicator=indicator,
            income_type='STUDENT_PAYMENT',
            is_processed=False,
        )
        PaymentAllocation.objects.create(
            transaction=tx, student=student, course=course, year=year, month=month, amount=amount
        )
        if offset_account:
            regenerate_accounting_entries([tx], user)
    return None


@login_required
def pending_payment_create(request):
    """Төлбөр төлсөнийг тэмдэглэх (AJAX).

    - BANK/POS: хуулга хүлээж буй тэмдэглэл (PendingPayment) — хуулгатай холбоход баталгаажна.
    - CASH: кассын орлогоор шууд бүртгэнэ (хуулга гэж байхгүй).
    - MIXED: бэлэн хэсгийг кассаар шууд, үлдсэнийг данс (хуулга хүлээж буй) гэж бүртгэнэ.
    """
    from django.db import transaction as db_transaction
    import json
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST хүсэлт шаардлагатай'})
    if not _can_mark_payments(request.user):
        return JsonResponse({'success': False, 'error': 'Төлбөр тэмдэглэх эрх танд байхгүй'})

    try:
        data = json.loads(request.body)
        student = UserProfile.objects.get(id=int(data.get('student')), role=UserRole.STUDENT)
        course = Course.objects.get(id=int(data.get('course')))
        year = int(data.get('year'))
        month = int(data.get('month'))
        amount = Decimal(str(data.get('amount') or '0'))
        paid_date = datetime.strptime(data.get('paid_date') or '', '%Y-%m-%d').date()
    except (UserProfile.DoesNotExist, Course.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Сурагч эсвэл анги олдсонгүй'})
    except Exception:
        return JsonResponse({'success': False, 'error': 'Мэдээлэл буруу байна'})

    if not 1 <= month <= 12:
        return JsonResponse({'success': False, 'error': 'Сар буруу байна'})
    if amount <= 0:
        return JsonResponse({'success': False, 'error': 'Дүн 0-ээс их байх ёстой'})

    method = data.get('method') or 'BANK'
    payer_name = (data.get('payer_name') or '').strip()
    comment = (data.get('comment') or '').strip()

    if method == 'MIXED':
        try:
            cash_amount = Decimal(str(data.get('cash_amount') or '0'))
        except Exception:
            return JsonResponse({'success': False, 'error': 'Бэлэн дүн буруу байна'})
        if cash_amount <= 0 or cash_amount >= amount:
            return JsonResponse({'success': False,
                                 'error': f'Бэлэн дүн 0-ээс их, нийт дүнгээс ({amount:,.0f}₮) бага байх ёстой'})
        with db_transaction.atomic():
            # Эхлээд кассыг бүртгэнэ — эс тэгвээс кассын хуваарилалт шинэ дансны тэмдэглэлийг холбож авна
            error = _record_cash_payment(
                request.user, student, course, year, month, cash_amount, paid_date, payer_name,
                cash_account_id=data.get('cash_account'),
            )
            if error:
                return JsonResponse({'success': False, 'error': error})
            PendingPayment.objects.create(
                student=student, course=course, year=year, month=month, amount=amount - cash_amount,
                paid_date=paid_date, method='BANK', payer_name=payer_name, comment=comment,
                created_by=request.user,
            )
        return JsonResponse({'success': True})

    if method == 'CASH':
        error = _record_cash_payment(
            request.user, student, course, year, month, amount, paid_date, payer_name,
            cash_account_id=data.get('cash_account'),
        )
        if error:
            return JsonResponse({'success': False, 'error': error})
        return JsonResponse({'success': True})

    if method not in dict(PendingPayment.METHOD_CHOICES):
        method = 'BANK'
    PendingPayment.objects.create(
        student=student, course=course, year=year, month=month, amount=amount,
        paid_date=paid_date, method=method,
        payer_name=payer_name,
        comment=comment,
        created_by=request.user,
    )
    return JsonResponse({'success': True})


@login_required
def pending_payment_delete(request, pending_id):
    """Хуулгатай холбогдоогүй тэмдэглэлийг устгах (AJAX)"""
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST хүсэлт шаардлагатай'})
    if not _can_mark_payments(request.user):
        return JsonResponse({'success': False, 'error': 'Устгах эрх танд байхгүй'})

    pending = PendingPayment.objects.filter(id=pending_id).first()
    if not pending:
        return JsonResponse({'success': False, 'error': 'Тэмдэглэл олдсонгүй'})
    if pending.is_matched:
        return JsonResponse({'success': False, 'error': 'Банкны гүйлгээтэй холбогдсон тул устгах боломжгүй. Эхлээд гүйлгээний холболтыг цуцлана уу.'})
    pending.delete()
    return JsonResponse({'success': True})


@login_required
def payment_discount_save(request):
    """Хөнгөлөлт өгөх/засах/устгах (AJAX).

    month..to_month хүртэлх сар бүрт ижил хөнгөлөлт өгнө. delete=true бол тухайн сарынхыг устгана.
    """
    import json
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST хүсэлт шаардлагатай'})
    if not _can_mark_payments(request.user):
        return JsonResponse({'success': False, 'error': 'Хөнгөлөлт өгөх эрх танд байхгүй'})

    try:
        data = json.loads(request.body)
        student = UserProfile.objects.get(id=int(data.get('student')), role=UserRole.STUDENT)
        course = Course.objects.get(id=int(data.get('course')))
        year = int(data.get('year'))
        month = int(data.get('month'))
        to_month = int(data.get('to_month') or month)
    except (UserProfile.DoesNotExist, Course.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Сурагч эсвэл анги олдсонгүй'})
    except Exception:
        return JsonResponse({'success': False, 'error': 'Мэдээлэл буруу байна'})
    if not 1 <= month <= to_month <= 12:
        return JsonResponse({'success': False, 'error': 'Сар буруу байна'})

    key = {'student': student, 'course': course, 'year': year}
    if data.get('delete'):
        PaymentDiscount.objects.filter(**key, month=month).delete()
        return JsonResponse({'success': True})

    name = (data.get('name') or '').strip()[:100]
    kind = data.get('kind')
    try:
        value = Decimal(str(data.get('value') or '0'))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Хөнгөлөлтийн хэмжээ буруу байна'})
    if not name:
        return JsonResponse({'success': False, 'error': 'Хөнгөлөлтийн нэр оруулна уу'})
    if kind not in dict(PaymentDiscount.KIND_CHOICES):
        return JsonResponse({'success': False, 'error': 'Хөнгөлөлтийн төрөл буруу байна'})
    if value <= 0 or (kind == 'PERCENT' and value > 100):
        return JsonResponse({'success': False, 'error': 'Хөнгөлөлт 0-ээс их (хувь бол 100 хүртэл) байх ёстой'})

    defaults = {'name': name, 'kind': kind, 'value': value,
                'comment': (data.get('comment') or '').strip(), 'created_by': request.user}
    for m in range(month, to_month + 1):
        PaymentDiscount.objects.update_or_create(**key, month=m, defaults=defaults)
    return JsonResponse({'success': True})


@login_required
def payment_cell_note_save(request):
    """Төлбөрийн хүснэгтийн нүдний тэмдэглэл, өнгийг хадгалах (AJAX). Хоёулаа хоосон бол устгана."""
    import json
    import re
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST хүсэлт шаардлагатай'})
    if not _can_mark_payments(request.user):
        return JsonResponse({'success': False, 'error': 'Засах эрх танд байхгүй'})

    try:
        data = json.loads(request.body)
        student = UserProfile.objects.get(id=int(data.get('student')), role=UserRole.STUDENT)
        course = Course.objects.get(id=int(data.get('course')))
        year = int(data.get('year'))
        month = int(data.get('month'))
    except (UserProfile.DoesNotExist, Course.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Сурагч эсвэл анги олдсонгүй'})
    except Exception:
        return JsonResponse({'success': False, 'error': 'Мэдээлэл буруу байна'})
    if not 1 <= month <= 12:
        return JsonResponse({'success': False, 'error': 'Сар буруу байна'})

    comment = (data.get('comment') or '').strip()
    color = (data.get('color') or '').strip()
    if color and not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        return JsonResponse({'success': False, 'error': 'Өнгө буруу байна'})

    key = {'student': student, 'course': course, 'year': year, 'month': month}
    if not comment and not color:
        PaymentCellNote.objects.filter(**key).delete()
    else:
        PaymentCellNote.objects.update_or_create(
            **key, defaults={'comment': comment, 'color': color, 'updated_by': request.user}
        )
    return JsonResponse({'success': True})
