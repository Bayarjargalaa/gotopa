from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from urllib.parse import urlencode
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from .models import (
    UserProfile, Course, Enrollment, Attendance, AttendanceWeekdayTemplate,
    AttendanceTeacherSelection, TeacherAttendance, CourseTeacherAssignment,
    UserRole, PageContent,
    Product, ProductCategory, StockMovement,
    Account, Counterparty, Transaction, Purchase, PurchaseItem, Sale, SaleItem,
    ChartOfAccounts, AccountingEntry, BankTransaction, CashFlowIndicator, PaymentAllocation,
    SalePaymentAllocation, BankTransferLink
)
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Sum, Count, F, Exists, OuterRef, Prefetch
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
import re
import os
from .import_counterparties import import_counterparties
from .import_bank_transactions import import_bank_transactions, next_entry_number

def home(request):
    """Нүүр хуудас"""
    return render(request, 'main/home.html')

def user_login(request):
    """Нэвтрэх - утас эсвэл имэйлээр"""
    if request.user.is_authenticated:
        return redirect('main:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')  # Утас эсвэл имэйл эсвэл username
        password = request.POST.get('password')
        
        # Backend автоматаар утас/имэйл/username-ээр шалгана
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            # Монгол нэр эсвэл username харуулах
            display_name = user.get_full_name() or user.username
            try:
                if hasattr(user, 'profile') and user.profile.mongolian_name:
                    display_name = user.profile.mongolian_name
            except:
                pass
            
            messages.success(request, f'Тавтай морил, {display_name}!')
            return redirect('main:dashboard')
        else:
            messages.error(request, 'Утас/имэйл эсвэл нууц үг буруу байна.')
    
    return render(request, 'main/login.html')

def user_logout(request):
    """Гарах"""
    logout(request)
    messages.success(request, 'Амжилттай гарлаа.')
    return redirect('main:home')

def register(request):
    """Бүртгүүлэх - Шинэ хэрэглэгч"""
    if request.user.is_authenticated:
        return redirect('main:dashboard')
    
    if request.method == 'POST':
        # Формоос өгөгдөл авах
        last_name = request.POST.get('last_name', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        # Backward compatibility - mongolian_name байвал хуваах
        mongolian_name = request.POST.get('mongolian_name', '').strip()
        if mongolian_name and not (last_name and first_name):
            parts = mongolian_name.split(maxsplit=1)
            last_name = parts[0] if len(parts) > 0 else ''
            first_name = parts[1] if len(parts) > 1 else parts[0]
        
        phone_number = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        district = request.POST.get('district', '').strip()
        birth_date = request.POST.get('birth_date', '').strip()
        enrollment_date = request.POST.get('enrollment_date', '').strip()
        gender = request.POST.get('gender', '').strip()
        profession = request.POST.get('profession', '').strip()
        education = request.POST.get('education', '').strip()
        current_job = request.POST.get('current_job', '').strip()
        facebook_name = request.POST.get('facebook_name', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        
        # Validation
        errors = []
        
        if not last_name or not first_name:
            errors.append('Овог, нэр оруулна уу.')
        
        if not phone_number:
            errors.append('Утасны дугаар оруулна уу.')
        
        if not gender:
            errors.append('Хүйс сонгоно уу.')
        
        course_ids = request.POST.getlist('courses')
        if not course_ids:
            errors.append('Дор хаяж 1 анги сонгоно уу.')
        else:
            # Утасны форматыг цэвэрлэх
            phone_clean = re.sub(r'[^\d+]', '', phone_number)
            if len(phone_clean) < 8:
                errors.append('Утасны дугаар хэт богино байна.')
        
        if not password1:
            errors.append('Нууц үг оруулна уу.')
        elif len(password1) < 8:
            errors.append('Нууц үг дор хаяж 8 тэмдэгт байх ёстой.')
        elif password1 != password2:
            errors.append('Нууц үг таарахгүй байна.')
        
        # Утас давхцаж байгаа эсэх шалгах
        phone_clean = re.sub(r'[^\d+]', '', phone_number)
        if UserProfile.objects.filter(phone__icontains=phone_clean[-8:]).exists():
            errors.append('Энэ утасны дугаар аль хэдийн бүртгэгдсэн байна.')
        
        # Имэйл давхцаж байгаа эсэх
        if email and User.objects.filter(email=email).exists():
            errors.append('Энэ имэйл хаяг аль хэдийн бүртгэгдсэн байна.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            courses = Course.objects.filter(is_active=True).order_by('-start_date')
            return render(request, 'main/register.html', {'courses': courses})
        
        try:
            # Username үүсгэх - утасны сүүлийн 8 орон
            username = f"student_{phone_clean[-8:]}"
            
            # Username давхцаж байгаа эсэх
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Энэ утасны дугаараар бүртгэл үүссэн байна.')
                courses = Course.objects.filter(is_active=True).order_by('-start_date')
                return render(request, 'main/register.html', {'courses': courses})
            
            # User үүсгэх
            user = User.objects.create_user(
                username=username,
                email=email if email else '',
                password=password1,
                first_name=mongolian_name.split()[0] if mongolian_name else '',
                last_name=' '.join(mongolian_name.split()[1:]) if len(mongolian_name.split()) > 1 else '',
            )
            
            # UserProfile үүсгэх
            profile = UserProfile.objects.create(
                user=user,
                last_name=last_name,
                first_name=first_name,
                phone=phone_clean,
                address=address,
                city=city,
                district=district,
                birth_date=birth_date if birth_date else None,
                enrollment_date=enrollment_date if enrollment_date else None,
                gender=gender if gender else None,
                profession=profession,
                education=education,
                current_job=current_job,
                facebook_name=facebook_name,
                role=UserRole.STUDENT,  # Автоматаар сурагч
                is_active_student=True,
            )
            
            # Сонгосон ангиудад бүртгүүлэх
            course_ids = request.POST.getlist('courses')
            enrolled_courses = []
            print(f"DEBUG: Сонгосон ангиуд (course_ids): {course_ids}")
            if course_ids:
                for course_id in course_ids:
                    try:
                        course = Course.objects.get(id=course_id, is_active=True)
                        print(f"DEBUG: Анги олдсон: {course.name}")
                        enrollment = Enrollment.objects.create(
                            student=profile,
                            course=course,
                            status='PENDING',  # Админ баталгаажуулах
                            is_active=True
                        )
                        print(f"DEBUG: Enrollment үүссэн: ID={enrollment.id}, student={profile.full_name}, course={course.name}, status={enrollment.status}")
                        enrolled_courses.append(course.name)
                    except Course.DoesNotExist:
                        print(f"DEBUG: Анги ID={course_id} олдсонгүй")
            else:
                print("DEBUG: Анги сонгоогүй байна")
            
            # Автоматаар нэвтрүүлэх - backend зааж өгөх
            login(request, user, backend='main.backends.PhoneOrEmailBackend')
            success_msg = f'Тавтай морил, {last_name} {first_name}! Та амжилттай бүртгүүллээ.'
            if enrolled_courses:
                success_msg += f'\nБүртгүүлсэн ангиуд: {", ".join(enrolled_courses)}'
            messages.success(request, success_msg)
            return redirect('main:dashboard')
            
        except Exception as e:
            messages.error(request, f'Бүртгэл үүсгэхэд алдаа гарлаа: {str(e)}')
            courses = Course.objects.filter(is_active=True).order_by('-start_date')
            return render(request, 'main/register.html', {'courses': courses}, {'courses': Course.objects.filter(is_active=True).order_by('-start_date')})
    
    # Идэвхтэй ангиудыг дамжуулах
    courses = Course.objects.filter(is_active=True).order_by('-start_date')
    return render(request, 'main/register.html', {'courses': courses})

@login_required
def dashboard(request):
    """Dashboard - Эрхийн дагуу өөр өөр мэдээлэл харуулах"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        # Хэрэв profile байхгүй бол үүсгэх (superuser-т зориулсан)
        # Superuser бол автоматаар PRESIDENT эрх өгөх
        role = UserRole.PRESIDENT if request.user.is_superuser else UserRole.STUDENT
        profile = UserProfile.objects.create(
            user=request.user,
            mongolian_name=request.user.get_full_name() or request.user.username,
            role=role
        )
    
    context = {
        'profile': profile,
    }
    
    # Тэргүүн, Захирал, Менежер - бүх мэдээлэл харна
    if profile.is_admin:
        context['total_students'] = UserProfile.objects.filter(role=UserRole.STUDENT).count()
        context['active_students'] = UserProfile.objects.filter(role=UserRole.STUDENT, is_active_student=True).count()
        context['total_teachers'] = UserProfile.objects.filter(role__in=[
            UserRole.TEACHER_BEGINNER,
            UserRole.TEACHER_INTERMEDIATE,
            UserRole.TEACHER_ADVANCED
        ]).count()
        context['total_courses'] = Course.objects.filter(is_active=True).count()
        context['recent_enrollments'] = Enrollment.objects.select_related('student', 'course').order_by('-enrolled_date')[:10]
        context['pending_enrollments'] = Enrollment.objects.filter(status='PENDING').count()  # Хүлээгдэж буй бүртгэл
        
        # Санхүүгийн статистик (Manager эсвэл Accountant бол)
        if profile.role in ['MANAGER', 'ACCOUNTANT'] or request.user.is_superuser:
            from django.db.models import Sum, Q, F
            from datetime import datetime, timedelta
            
            # Сүүлийн сарын өгөгдөл
            last_month = datetime.now() - timedelta(days=30)
            
            # Орлого (банкны гүйлгээ)
            total_income = BankTransaction.objects.filter(
                income_amount__gt=0,
                transaction_date__gte=last_month
            ).aggregate(total=Sum('income_amount'))['total'] or 0
            
            # Зарлага (банкны гүйлгээ)
            total_expense = BankTransaction.objects.filter(
                expense_amount__gt=0,
                transaction_date__gte=last_month
            ).aggregate(total=Sum('expense_amount'))['total'] or 0
            
            # Худалдан авалт (сүүлийн сарын)
            purchases = StockMovement.objects.filter(
                movement_type='IN',
                created_at__gte=last_month
            )
            total_purchases = sum(p.quantity * (p.price or 0) for p in purchases)
            
            # Борлуулалт (сүүлийн сарын)
            sales = StockMovement.objects.filter(
                movement_type='OUT',
                created_at__gte=last_month
            )
            total_sales = sum(s.quantity * (s.price or 0) for s in sales)
            
            context['total_income'] = total_income
            context['total_expense'] = total_expense
            context['total_purchases'] = total_purchases
            context['total_sales'] = total_sales
        
    # Багш - өөрийн заадаг хичээлүүд
    elif profile.is_teacher:
        context['my_courses'] = Course.objects.filter(
            Q(teacher=profile) | Q(teacher_assignments__teacher=profile),
            is_active=True
        ).distinct()
        context['total_students'] = sum(course.enrolled_count for course in context['my_courses'])
        
    # Сурагч - элссэн хичээлүүд
    else:
        context['my_enrollments'] = Enrollment.objects.filter(
            student=profile,
            is_active=True
        ).select_related('course')
        context['pending_payments'] = context['my_enrollments'].filter(is_paid=False)
    
    return render(request, 'main/dashboard.html', context)

@login_required
def profile_view(request):
    """Хувийн мэдээлэл харах/засах"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    return render(request, 'main/profile.html', {'profile': profile})

@login_required
def student_list(request):
    """Сурагчдын жагсаалт - Админ, менежер, багш"""
    profile = request.user.profile
    if not (profile.is_admin or profile.is_manager or profile.is_teacher):
        messages.error(request, 'Хандах эрхгүй байна.')
        return redirect('main:dashboard')

    students = UserProfile.objects.filter(role=UserRole.STUDENT).select_related('user').prefetch_related(
        'enrollments__course'
    ).order_by('-enrollment_date')

    total_students = students.count()

    q = request.GET.get('q', '').strip()
    active = request.GET.get('active', '').strip()
    enrollment_status = request.GET.get('enrollment_status', '').strip()
    course_id = request.GET.get('course', '').strip()
    sort = request.GET.get('sort', 'name_asc').strip()

    if q:
        searchable_fields = [
            'mongolian_name',
            'user__first_name',
            'user__last_name',
            'user__username',
            'user__email',
            'phone',
            'address',
            'city',
            'district',
            'profession',
            'current_job',
            'enrollments__course__name',
            'enrollments__course__level',
        ]

        # iucontains — Кирилл үсгийг ч том/жижиг ялгахгүй хайна (main/db_lookups.py)
        search_query = Q()
        for field in searchable_fields:
            search_query |= Q(**{f'{field}__iucontains': q})

        students = students.filter(search_query)

    if active == '1':
        students = students.filter(is_active_student=True)
    elif active == '0':
        students = students.filter(is_active_student=False)

    allowed_enrollment_statuses = {choice[0] for choice in Enrollment.STATUS_CHOICES}
    if enrollment_status in allowed_enrollment_statuses:
        students = students.filter(enrollments__status=enrollment_status)

    if course_id.isdigit():
        students = students.filter(enrollments__course_id=course_id)

    students = students.distinct()

    sort_options = {
        'name_asc': ['first_name', 'last_name', 'mongolian_name', 'user__username'],
        'name_desc': ['-first_name', '-last_name', '-mongolian_name', '-user__username'],
        'surname_asc': ['last_name', 'first_name', 'mongolian_name', 'user__username'],
        'surname_desc': ['-last_name', '-first_name', '-mongolian_name', '-user__username'],
        'enrollment_newest': ['-enrollment_date', 'first_name', 'last_name'],
        'enrollment_oldest': ['enrollment_date', 'first_name', 'last_name'],
        'phone_asc': ['phone', 'first_name', 'last_name'],
    }
    students = students.order_by(*sort_options.get(sort, sort_options['name_asc']))
    filtered_count = students.count()

    class_counts = {
        'BEGINNER_1': 0,
        'BEGINNER_2': 0,
        'INTERMEDIATE': 0,
        'ADVANCED': 0,
    }
    status_labels = dict(Enrollment.STATUS_CHOICES)
    class_status_counts = {level: {status: 0 for status in status_labels} for level in class_counts}

    enrollment_counts = (
        Enrollment.objects
        .filter(student__in=students)
        .values('course__level')
        .annotate(student_count=Count('student', distinct=True))
    )

    for row in enrollment_counts:
        level = row['course__level']
        if level in class_counts:
            class_counts[level] = row['student_count']

    level_status_rows = (
        Enrollment.objects
        .filter(student__in=students)
        .values('course__level', 'status')
        .annotate(student_count=Count('student', distinct=True))
    )
    for row in level_status_rows:
        level = row['course__level']
        status = row['status']
        if level in class_status_counts and status in class_status_counts[level]:
            class_status_counts[level][status] = row['student_count']

    status_counts = {choice[0]: 0 for choice in Enrollment.STATUS_CHOICES}
    status_count_rows = (
        Enrollment.objects
        .filter(student__in=students)
        .values('status')
        .annotate(student_count=Count('student', distinct=True))
    )
    for row in status_count_rows:
        status = row['status']
        if status in status_counts:
            status_counts[status] = row['student_count']

    status_short_labels = {
        'PENDING': 'Хүлээгдэж буй',
        'APPROVED': 'Баталсан',
        'COMPLETED': 'Төгссөн',
        'CANCELLED': 'Цуцалсан',
    }

    def status_breakdown(counts_by_status):
        return [
            {'label': status_short_labels.get(status, status), 'value': count}
            for status, count in counts_by_status.items()
            if count
        ]

    stats = [
        {'label': 'Нийт сурагч', 'value': total_students, 'accent': 'bg-secondary', 'breakdown': status_breakdown(status_counts)},
        {'label': 'Харагдаж буй', 'value': filtered_count, 'accent': 'bg-primary', 'breakdown': status_breakdown(status_counts)},
        {'label': 'Анхан 1', 'value': class_counts['BEGINNER_1'], 'accent': 'bg-green-500', 'breakdown': status_breakdown(class_status_counts['BEGINNER_1'])},
        {'label': 'Анхан 2', 'value': class_counts['BEGINNER_2'], 'accent': 'bg-emerald-500', 'breakdown': status_breakdown(class_status_counts['BEGINNER_2'])},
        {'label': 'Дунд', 'value': class_counts['INTERMEDIATE'], 'accent': 'bg-blue-500', 'breakdown': status_breakdown(class_status_counts['INTERMEDIATE'])},
        {'label': 'Ахисан', 'value': class_counts['ADVANCED'], 'accent': 'bg-purple-500', 'breakdown': status_breakdown(class_status_counts['ADVANCED'])},
    ]

    context = {
        'students': students,
        'q': q,
        'active': active,
        'enrollment_status': enrollment_status,
        'status_choices': Enrollment.STATUS_CHOICES,
        'course_id': course_id,
        'courses': Course.objects.filter(is_active=True).order_by('name'),
        'sort': sort,
        'total_students': total_students,
        'filtered_count': filtered_count,
        'stats': stats,
    }
    return render(request, 'main/students.html', context)


@login_required
def student_bulk_edit(request):
    """Сурагчийн анги бүртгэлийн болон идэвхийн төлөвийг бөөнөөр шинэчлэх."""
    profile = request.user.profile
    if not (profile.is_admin or profile.is_manager):
        messages.error(request, 'Хандах эрхгүй байна.')
        return redirect('main:dashboard')

    first_name = request.GET.get('first_name', '').strip()
    last_name = request.GET.get('last_name', '').strip()
    phone = request.GET.get('phone', '').strip()
    course_name = request.GET.get('course_name', '').strip()
    enrollment_date_from = request.GET.get('enrollment_date_from', '').strip()
    enrollment_date_to = request.GET.get('enrollment_date_to', '').strip()
    sort_field = request.GET.get('sort_field', 'first_name').strip()
    sort_direction = request.GET.get('sort_direction', 'asc').strip()

    sort_fields = {
        'first_name': 'Нэр',
        'last_name': 'Овог',
        'phone': 'Утасны дугаар',
        'course_name': 'Элссэн анги',
        'enrollment_date': 'Элссэн огноо',
    }
    if sort_field not in sort_fields:
        sort_field = 'first_name'
    if sort_direction not in {'asc', 'desc'}:
        sort_direction = 'asc'

    student_queryset = UserProfile.objects.filter(role=UserRole.STUDENT)
    if first_name:
        student_queryset = student_queryset.filter(first_name__iucontains=first_name)
    if last_name:
        student_queryset = student_queryset.filter(last_name__iucontains=last_name)
    if phone:
        student_queryset = student_queryset.filter(phone__icontains=phone)
    if course_name:
        student_queryset = student_queryset.filter(
            enrollments__course__name__iucontains=course_name
        )
    if enrollment_date_from:
        student_queryset = student_queryset.filter(
            enrollments__enrolled_date__gte=enrollment_date_from
        )
    if enrollment_date_to:
        student_queryset = student_queryset.filter(
            enrollments__enrolled_date__lte=enrollment_date_to
        )

    enrollment_queryset = Enrollment.objects.select_related('course')
    if course_name:
        enrollment_queryset = enrollment_queryset.filter(
            course__name__iucontains=course_name
        )
    if enrollment_date_from:
        enrollment_queryset = enrollment_queryset.filter(
            enrolled_date__gte=enrollment_date_from
        )
    if enrollment_date_to:
        enrollment_queryset = enrollment_queryset.filter(
            enrolled_date__lte=enrollment_date_to
        )

    students = list(
        student_queryset
        .select_related('user')
        .prefetch_related(Prefetch('enrollments', queryset=enrollment_queryset))
    )

    def student_sort_key(student):
        if sort_field == 'first_name':
            return (student.first_name or student.mongolian_name or student.user.username).casefold()
        if sort_field == 'last_name':
            return (student.last_name or student.mongolian_name or student.user.username).casefold()
        if sort_field == 'phone':
            return student.phone or ''

        enrollments = list(student.enrollments.all())
        if sort_field == 'course_name':
            return min(
                (enrollment.course.name.casefold() for enrollment in enrollments),
                default='',
            )
        return min(
            (enrollment.enrolled_date for enrollment in enrollments),
            default=date.min,
        )

    students.sort(key=student_sort_key, reverse=sort_direction == 'desc')

    if request.method == 'POST':
        allowed_statuses = {choice[0] for choice in Enrollment.STATUS_CHOICES}
        enrollment_ids = {
            enrollment.id
            for student in students
            for enrollment in student.enrollments.all()
        }
        changed_enrollments = 0

        with transaction.atomic():
            for student in students:
                active_value = request.POST.get(f'student_active_{student.id}')
                if active_value in {'1', '0'}:
                    new_active = active_value == '1'
                    if student.is_active_student != new_active:
                        student.is_active_student = new_active
                        student.save(update_fields=['is_active_student', 'updated_at'])

                for enrollment in student.enrollments.all():
                    if enrollment.id not in enrollment_ids:
                        continue
                    selected_status = request.POST.get(f'enrollment_status_{enrollment.id}')
                    if selected_status in allowed_statuses and selected_status != enrollment.status:
                        enrollment.status = selected_status
                        enrollment.is_active = selected_status != 'CANCELLED'
                        enrollment.save(update_fields=['status', 'is_active'])
                        changed_enrollments += 1

        messages.success(request, f'{len(students)} сурагчийн мэдээлэл хадгалагдлаа. {changed_enrollments} ангийн төлөв шинэчлэгдэв.')
        query_params = request.GET.urlencode()
        redirect_url = f"{reverse('main:student_bulk_edit')}?{query_params}" if query_params else reverse('main:student_bulk_edit')
        return redirect(redirect_url)

    return render(request, 'main/student_bulk_edit.html', {
        'students': students,
        'status_choices': Enrollment.STATUS_CHOICES,
        'first_name': first_name,
        'last_name': last_name,
        'phone': phone,
        'course_name': course_name,
        'enrollment_date_from': enrollment_date_from,
        'enrollment_date_to': enrollment_date_to,
        'sort_field': sort_field,
        'sort_direction': sort_direction,
        'sort_fields': sort_fields,
    })

@login_required
def student_create(request):
    """Сурагч бүртгэх - Админ эсвэл менежер"""
    profile = request.user.profile
    if not (profile.is_admin or profile.is_manager):
        messages.error(request, 'Танд сурагч бүртгэх эрх байхгүй байна.')
        return redirect('main:student_list')
    
    # Идэвхтэй сургалтууд
    courses = Course.objects.filter(is_active=True).order_by('-start_date')
    
    if request.method == 'POST':
        # Форм мэдээлэл авах
        last_name = request.POST.get('last_name', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        enrollment_date = request.POST.get('enrollment_date', '').strip()
        
        # Validation
        if not last_name or not first_name:
            messages.error(request, 'Овог, нэр оруулна уу.')
            courses = Course.objects.filter(is_active=True).order_by('-start_date')
            return render(request, 'main/student_create.html', {'courses': courses})
        
        if not phone:
            messages.error(request, 'Утасны дугаар оруулна уу.')
            courses = Course.objects.filter(is_active=True).order_by('-start_date')
            return render(request, 'main/student_create.html', {'courses': courses})
        
        # Утасны дугаар цэвэрлэх (зай, - тэмдэг арилгах)
        phone_clean = phone.replace(' ', '').replace('-', '').replace('+976', '')
        
        # Утасны дугаарын формат шалгах
        if not re.match(r'^\d{8}$', phone_clean):
            messages.error(request, 'Утасны дугаар 8 оронтой тоо байх ёстой. Жишээ: 99001234')
            courses = Course.objects.filter(is_active=True).order_by('-start_date')
            return render(request, 'main/student_create.html', {'courses': courses})
        
        # Утас давхцаж байгаа эсэх шалгах
        if UserProfile.objects.filter(phone=phone_clean).exists():
            messages.error(request, f'Утасны дугаар {phone_clean} аль хэдийн бүртгэгдсэн байна.')
            courses = Course.objects.filter(is_active=True).order_by('-start_date')
            return render(request, 'main/student_create.html', {'courses': courses})
        
        # Имэйл давхцаж байгаа эсэх шалгах
        if email and User.objects.filter(email=email).exists():
            messages.error(request, f'Имэйл хаяг {email} аль хэдийн бүртгэгдсэн байна.')
            courses = Course.objects.filter(is_active=True).order_by('-start_date')
            return render(request, 'main/student_create.html', {'courses': courses})
        
        try:
            # Username үүсгэх - student_утасны_сүүлийн_8_орон
            if len(phone_clean) >= 8:
                username = f"student_{phone_clean[-8:]}"
            else:
                username = f"student_{phone_clean}"
            
            # Username давхцаж байгаа эсэх шалгах
            counter = 1
            original_username = username
            while User.objects.filter(username=username).exists():
                username = f"{original_username}_{counter}"
                counter += 1
            
            # User үүсгэх
            user = User.objects.create_user(
                username=username,
                email=email if email else '',
                password=phone_clean[-8:] if len(phone_clean) >= 8 else phone_clean,  # Анхны нууц үг
                first_name=first_name,
                last_name=last_name,
            )
            
            # UserProfile үүсгэх
            from datetime import date
            parsed_enrollment_date = None
            if enrollment_date:
                try:
                    parsed_enrollment_date = date.fromisoformat(enrollment_date)
                except:
                    parsed_enrollment_date = timezone.now().date()
            else:
                parsed_enrollment_date = timezone.now().date()
            
            student_profile = UserProfile.objects.create(
                user=user,
                last_name=last_name,
                first_name=first_name,
                phone=phone_clean,
                address=address,
                role=UserRole.STUDENT,
                is_active_student=True,
                enrollment_date=parsed_enrollment_date
            )
            
            # Сургалт сонгосон бол Enrollment үүсгэх
            course_ids = request.POST.getlist('courses')
            enrolled_courses = []
            if course_ids:
                for course_id in course_ids:
                    try:
                        course = Course.objects.get(id=course_id, is_active=True)
                        Enrollment.objects.create(
                            student=student_profile,
                            course=course,
                            status='APPROVED',
                            is_active=True
                        )
                        enrolled_courses.append(course.name)
                    except Course.DoesNotExist:
                        pass
            
            success_msg = f'✓ Сурагч "{last_name} {first_name}" амжилттай бүртгэгдлээ!\nUsername: {username}\nНууц үг: {phone_clean[-8:] if len(phone_clean) >= 8 else phone_clean}'
            if enrolled_courses:
                success_msg += f'\nБүртгүүлсэн сургалтууд: {", ".join(enrolled_courses)}'
            
            messages.success(request, success_msg)
            return redirect('main:student_list')
            
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
            return render(request, 'main/student_create.html', {'courses': courses})
    
    return render(request, 'main/student_create.html', {'courses': courses})

@login_required
def student_update(request, student_id):
    """Сурагч засах - Админ эсвэл менежер"""
    profile = request.user.profile
    if not (profile.is_admin or profile.is_manager):
        messages.error(request, 'Танд сурагч засах эрх байхгүй байна.')
        return redirect('main:student_list')
    
    student_profile = get_object_or_404(UserProfile, id=student_id, role=UserRole.STUDENT)
    
    # Идэвхтэй сургалтууд болон одоогийн бүртгэлүүд
    courses = Course.objects.filter(is_active=True).order_by('-start_date')
    enrollments = Enrollment.objects.filter(student=student_profile).select_related('course')
    enrolled_course_ids = list(enrollments.values_list('course_id', flat=True))
    
    if request.method == 'POST':
        # Форм мэдээлэл авах
        last_name = request.POST.get('last_name', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        birth_date = request.POST.get('birth_date', '').strip()
        gender = request.POST.get('gender', '').strip()
        city = request.POST.get('city', '').strip()
        district = request.POST.get('district', '').strip()
        address = request.POST.get('address', '').strip()
        notes = request.POST.get('notes', '').strip()
        profession = request.POST.get('profession', '').strip()
        education = request.POST.get('education', '').strip()
        current_job = request.POST.get('current_job', '').strip()
        facebook_name = request.POST.get('facebook_name', '').strip()
        enrollment_date = request.POST.get('enrollment_date', '').strip()
        photo = request.FILES.get('photo')
        is_active = request.POST.get('is_active') == 'on'
        
        # Validation
        if not last_name or not first_name:
            messages.error(request, 'Овог, нэр оруулна уу.')
            return render(request, 'main/student_update.html', {'student': student_profile})
        
        if not phone:
            messages.error(request, 'Утасны дугаар оруулна уу.')
            return render(request, 'main/student_update.html', {'student': student_profile})
        
        # Утасны дугаар цэвэрлэх
        phone_clean = phone.replace(' ', '').replace('-', '').replace('+976', '')
        
        # Утасны дугаарын формат шалгах
        if not re.match(r'^\d{8}$', phone_clean):
            messages.error(request, 'Утасны дугаар 8 оронтой тоо байх ёстой. Жишээ: 99001234')
            return render(request, 'main/student_update.html', {'student': student_profile})
        
        # Утас давхцаж байгаа эсэх шалгах (өөр сурагчтай)
        if UserProfile.objects.filter(phone=phone_clean).exclude(id=student_id).exists():
            messages.error(request, f'Утасны дугаар {phone_clean} аль хэдийн бүртгэгдсэн байна.')
            return render(request, 'main/student_update.html', {'student': student_profile})
        
        # Имэйл давхцаж байгаа эсэх шалгах (өөр хэрэглэгчтэй)
        if email and User.objects.filter(email=email).exclude(id=student_profile.user.id).exists():
            messages.error(request, f'Имэйл хаяг {email} аль хэдийн бүртгэгдсэн байна.')
            return render(request, 'main/student_update.html', {'student': student_profile})
        
        try:
            # User мэдээлэл шинэчлэх
            user = student_profile.user
            user.first_name = first_name
            user.last_name = last_name
            user.email = email if email else ''
            user.save()
            
            # UserProfile шинэчлэх
            from datetime import date
            student_profile.last_name = last_name
            student_profile.first_name = first_name
            student_profile.phone = phone_clean
            student_profile.birth_date = birth_date if birth_date else None
            student_profile.gender = gender if gender else ''
            student_profile.city = city
            student_profile.district = district
            student_profile.address = address
            student_profile.notes = notes
            student_profile.profession = profession
            student_profile.education = education
            student_profile.current_job = current_job
            student_profile.facebook_name = facebook_name
            student_profile.is_active_student = is_active
            
            # Элссэн огноо шинэчлэх
            if enrollment_date:
                try:
                    student_profile.enrollment_date = date.fromisoformat(enrollment_date)
                except:
                    pass
            
            # Зураг шинэчлэх (хэрэв байвал)
            if photo:
                student_profile.photo = photo
            
            student_profile.save()
            
            # Сургалт бүртгэл шинэчлэх
            status_changed_count = 0
            enrollment_date_changed_count = 0
            allowed_statuses = {'PENDING', 'APPROVED', 'COMPLETED', 'CANCELLED'}
            for enrollment in enrollments:
                selected_status = request.POST.get(f'enrollment_status_{enrollment.id}', '').strip()
                selected_enrollment_date = request.POST.get(
                    f'enrollment_date_{enrollment.id}', ''
                ).strip()
                enrollment_changed = False

                if selected_status in allowed_statuses and selected_status != enrollment.status:
                    enrollment.status = selected_status
                    # Цуцалсан төлөвт идэвхгүй, бусад үед идэвхтэй байлгана
                    enrollment.is_active = selected_status != 'CANCELLED'
                    status_changed_count += 1
                    enrollment_changed = True

                if selected_enrollment_date:
                    try:
                        parsed_enrollment_date = date.fromisoformat(selected_enrollment_date)
                        if parsed_enrollment_date != enrollment.enrolled_date:
                            enrollment.enrolled_date = parsed_enrollment_date
                            enrollment_date_changed_count += 1
                            enrollment_changed = True
                    except ValueError:
                        messages.error(
                            request,
                            f'{enrollment.course.name} сургалтын элссэн огноо буруу байна.'
                        )
                        return render(request, 'main/student_update.html', {
                            'student': student_profile,
                            'courses': courses,
                            'enrollments': enrollments,
                            'enrolled_course_ids': enrolled_course_ids
                        })

                if enrollment_changed:
                    enrollment.save()

            new_course_ids = request.POST.getlist('new_courses')
            added_courses = []
            if new_course_ids:
                for course_id in new_course_ids:
                    try:
                        course = Course.objects.get(id=course_id, is_active=True)
                        # Аль хэдийн бүртгэгдсэн эсэх шалгах
                        if not Enrollment.objects.filter(student=student_profile, course=course).exists():
                            Enrollment.objects.create(
                                student=student_profile,
                                course=course,
                                status='APPROVED',
                                is_active=True
                            )
                            added_courses.append(course.name)
                    except Course.DoesNotExist:
                        pass
            
            success_msg = f'✓ Сурагч "{last_name} {first_name}" амжилттай шинэчлэгдлээ!'
            if status_changed_count:
                success_msg += f'\nТөлөв шинэчлэгдсэн бүртгэл: {status_changed_count}'
            if enrollment_date_changed_count:
                success_msg += f'\nЭлссэн огноо шинэчлэгдсэн бүртгэл: {enrollment_date_changed_count}'
            if added_courses:
                success_msg += f'\nШинээр нэмэгдсэн сургалтууд: {", ".join(added_courses)}'
            
            messages.success(request, success_msg)
            return redirect('main:student_list')
            
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
            return render(request, 'main/student_update.html', {
                'student': student_profile,
                'courses': courses,
                'enrollments': enrollments,
                'enrolled_course_ids': enrolled_course_ids
            })
    
    return render(request, 'main/student_update.html', {
        'student': student_profile,
        'courses': courses,
        'enrollments': enrollments,
        'enrolled_course_ids': enrolled_course_ids
    })

@login_required
def student_delete(request, student_id):
    """Сурагч устгах - Админ эсвэл менежер"""
    profile = request.user.profile
    if not (profile.is_admin or profile.is_manager):
        messages.error(request, 'Танд сурагч устгах эрх байхгүй байна.')
        return redirect('main:student_list')
    
    student_profile = get_object_or_404(UserProfile, id=student_id, role=UserRole.STUDENT)
    
    if request.method == 'POST':
        student_name = student_profile.mongolian_name or student_profile.user.username
        user = student_profile.user
        
        try:
            # User устгахад profile автоматаар устана (CASCADE)
            user.delete()
            messages.success(request, f'✓ Сурагч "{student_name}" амжилттай устгагдлаа.')
            return redirect('main:student_list')
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
            return redirect('main:student_list')
    
    return redirect('main:student_list')

@login_required
def teacher_list(request):
    """Багш нарын жагсаалт - Зөвхөн админ"""
    if not request.user.profile.is_admin:
        messages.error(request, 'Хандах эрхгүй байна.')
        return redirect('main:dashboard')
    
    teachers = UserProfile.objects.filter(
        role__in=[UserRole.TEACHER_BEGINNER, UserRole.TEACHER_INTERMEDIATE, UserRole.TEACHER_ADVANCED]
    ).select_related('user').prefetch_related('course_assignments__course')
    return render(request, 'main/teacher_list.html', {'teachers': teachers})

@login_required
def teacher_create(request):
    """Багш бүртгэх - Зөвхөн админ"""
    if not request.user.profile.is_admin:
        messages.error(request, 'Танд багш бүртгэх эрх байхгүй байна.')
        return redirect('main:teacher_list')
    
    if request.method == 'POST':
        # Форм мэдээлэл авах
        last_name = request.POST.get('last_name', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        # Backward compatibility: хуучин form-оос mongolian_name ирвэл овог/нэр рүү задлах
        mongolian_name = request.POST.get('mongolian_name', '').strip()
        if mongolian_name and not (last_name and first_name):
            parts = mongolian_name.split(maxsplit=1)
            last_name = parts[0] if len(parts) > 0 else ''
            first_name = parts[1] if len(parts) > 1 else parts[0]
        phone = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        selected_levels = request.POST.getlist('teacher_level_choices')
        # Нэвтрэх эрхэд ашиглах гол role (эхний сонголт)
        role = selected_levels[0] if selected_levels else ''
        teacher_levels_str = ','.join(selected_levels)
        
        # Validation
        _courses_ctx = {'courses': Course.objects.all().order_by('level', 'name')}
        if not last_name or not first_name:
            messages.error(request, 'Овог, нэр оруулна уу.')
            return render(request, 'main/teacher_create.html', _courses_ctx)
        
        if not phone:
            messages.error(request, 'Утасны дугаар оруулна уу.')
            return render(request, 'main/teacher_create.html', _courses_ctx)
        
        if not selected_levels:
            messages.error(request, 'Багшийн түвшин сонгоно уу.')
            return render(request, 'main/teacher_create.html', _courses_ctx)
        
        # Утасны дугаар цэвэрлэх
        phone_clean = phone.replace(' ', '').replace('-', '').replace('+976', '')
        
        # Утасны дугаарын формат шалгах
        if not re.match(r'^\d{8}$', phone_clean):
            messages.error(request, 'Утасны дугаар 8 оронтой тоо байх ёстой. Жишээ: 99001234')
            return render(request, 'main/teacher_create.html', _courses_ctx)
        
        # Утас давхцаж байгаа эсэх шалгах
        if UserProfile.objects.filter(phone=phone_clean).exists():
            messages.error(request, f'Утасны дугаар {phone_clean} аль хэдийн бүртгэгдсэн байна.')
            return render(request, 'main/teacher_create.html', _courses_ctx)
        
        # Имэйл давхцаж байгаа эсэх шалгах
        if email and User.objects.filter(email=email).exists():
            messages.error(request, f'Имэйл хаяг {email} аль хэдийн бүртгэгдсэн байна.')
            return render(request, 'main/teacher_create.html', _courses_ctx)
        
        try:
            # Username үүсгэх
            if len(phone_clean) >= 8:
                username = f"teacher_{phone_clean[-8:]}"
            else:
                username = f"teacher_{phone_clean}"
            
            # Username давхцаж байгаа эсэх шалгах
            counter = 1
            original_username = username
            while User.objects.filter(username=username).exists():
                username = f"{original_username}_{counter}"
                counter += 1
            
            # User үүсгэх
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email if email else '',
                password=phone_clean[-8:] if len(phone_clean) >= 8 else phone_clean
            )
            
            # UserProfile үүсгэх
            new_profile = UserProfile.objects.create(
                user=user,
                last_name=last_name,
                first_name=first_name,
                phone=phone_clean,
                address=address,
                role=role,
                teacher_levels=teacher_levels_str,
                enrollment_date=timezone.now().date()
            )

            # Сонгосон ангиудыг оноох
            course_ids = request.POST.getlist('course_ids')
            if course_ids:
                CourseTeacherAssignment.objects.bulk_create(
                    [
                        CourseTeacherAssignment(course_id=course_id, teacher=new_profile)
                        for course_id in course_ids if str(course_id).isdigit()
                    ],
                    ignore_conflicts=True
                )

            messages.success(
                request,
                f'✓ Багш "{last_name} {first_name}" амжилттай бүртгэгдлээ!\n'
                f'Username: {username}\n'
                f'Нууц үг: {phone_clean[-8:] if len(phone_clean) >= 8 else phone_clean}'
            )
            return redirect('main:teacher_list')
            
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
            courses = Course.objects.all().order_by('level', 'name')
            return render(request, 'main/teacher_create.html', {'courses': courses})
    
    courses = Course.objects.all().order_by('level', 'name')
    return render(request, 'main/teacher_create.html', {'courses': courses})

@login_required
def teacher_update(request, teacher_id):
    """Багш засах - Зөвхөн админ"""
    if not request.user.profile.is_admin:
        messages.error(request, 'Танд багш засах эрх байхгүй байна.')
        return redirect('main:teacher_list')
    
    teacher_profile = get_object_or_404(
        UserProfile, 
        id=teacher_id, 
        role__in=[UserRole.TEACHER_BEGINNER, UserRole.TEACHER_INTERMEDIATE, UserRole.TEACHER_ADVANCED]
    )
    
    if request.method == 'POST':
        # Форм мэдээлэл авах
        last_name = request.POST.get('last_name', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        selected_levels = request.POST.getlist('teacher_level_choices')
        role = selected_levels[0] if selected_levels else ''
        teacher_levels_str = ','.join(selected_levels)
        birth_date = request.POST.get('birth_date', '').strip()
        gender = request.POST.get('gender', '').strip()
        city = request.POST.get('city', '').strip()
        district = request.POST.get('district', '').strip()
        notes = request.POST.get('notes', '').strip()
        photo = request.FILES.get('photo')
        
        # Validation
        if not last_name or not first_name:
            messages.error(request, 'Овог, нэр оруулна уу.')
            courses = Course.objects.all().order_by('level', 'name')
            teacher_course_ids = list(teacher_profile.course_assignments.values_list('course_id', flat=True))
            return render(request, 'main/teacher_update.html', {'teacher': teacher_profile, 'courses': courses, 'teacher_course_ids': teacher_course_ids})
        
        if not phone:
            messages.error(request, 'Утасны дугаар оруулна уу.')
            courses = Course.objects.all().order_by('level', 'name')
            teacher_course_ids = list(teacher_profile.course_assignments.values_list('course_id', flat=True))
            return render(request, 'main/teacher_update.html', {'teacher': teacher_profile, 'courses': courses, 'teacher_course_ids': teacher_course_ids})
        
        if not selected_levels:
            messages.error(request, 'Багшийн түвшин сонгоно уу.')
            courses = Course.objects.all().order_by('level', 'name')
            teacher_course_ids = list(teacher_profile.course_assignments.values_list('course_id', flat=True))
            return render(request, 'main/teacher_update.html', {'teacher': teacher_profile, 'courses': courses, 'teacher_course_ids': teacher_course_ids})
        
        # Утасны дугаар цэвэрлэх
        phone_clean = phone.replace(' ', '').replace('-', '').replace('+976', '')
        
        # Утасны дугаарын формат шалгах
        if not re.match(r'^\d{8}$', phone_clean):
            messages.error(request, 'Утасны дугаар 8 оронтой тоо байх ёстой. Жишээ: 99001234')
            courses = Course.objects.all().order_by('level', 'name')
            teacher_course_ids = list(teacher_profile.course_assignments.values_list('course_id', flat=True))
            return render(request, 'main/teacher_update.html', {'teacher': teacher_profile, 'courses': courses, 'teacher_course_ids': teacher_course_ids})
        
        # Утас давхцаж байгаа эсэх шалгах (өөр хэрэглэгчтэй)
        if UserProfile.objects.filter(phone=phone_clean).exclude(id=teacher_id).exists():
            messages.error(request, f'Утасны дугаар {phone_clean} аль хэдийн бүртгэгдсэн байна.')
            courses = Course.objects.all().order_by('level', 'name')
            teacher_course_ids = list(teacher_profile.course_assignments.values_list('course_id', flat=True))
            return render(request, 'main/teacher_update.html', {'teacher': teacher_profile, 'courses': courses, 'teacher_course_ids': teacher_course_ids})
        
        # Имэйл давхцаж байгаа эсэх шалгах (өөр хэрэглэгчтэй)
        if email and User.objects.filter(email=email).exclude(id=teacher_profile.user.id).exists():
            messages.error(request, f'Имэйл хаяг {email} аль хэдийн бүртгэгдсэн байна.')
            courses = Course.objects.all().order_by('level', 'name')
            teacher_course_ids = list(teacher_profile.course_assignments.values_list('course_id', flat=True))
            return render(request, 'main/teacher_update.html', {'teacher': teacher_profile, 'courses': courses, 'teacher_course_ids': teacher_course_ids})
        
        try:
            # User мэдээлэл шинэчлэх
            user = teacher_profile.user
            user.first_name = first_name
            user.last_name = last_name
            user.email = email if email else ''
            user.save()
            
            # UserProfile шинэчлэх
            teacher_profile.last_name = last_name
            teacher_profile.first_name = first_name
            teacher_profile.phone = phone_clean
            teacher_profile.role = role
            teacher_profile.teacher_levels = teacher_levels_str
            teacher_profile.birth_date = birth_date if birth_date else None
            teacher_profile.gender = gender if gender else ''
            teacher_profile.city = city
            teacher_profile.district = district
            teacher_profile.address = address
            teacher_profile.notes = notes
            
            # Зураг шинэчлэх (хэрэв байвал)
            if photo:
                teacher_profile.photo = photo
            
            teacher_profile.save()

            # Ангийн оноолт шинэчлэх
            course_ids = [int(cid) for cid in request.POST.getlist('course_ids')]
            CourseTeacherAssignment.objects.filter(teacher=teacher_profile).exclude(course_id__in=course_ids).delete()
            existing_course_ids = set(
                CourseTeacherAssignment.objects.filter(teacher=teacher_profile).values_list('course_id', flat=True)
            )
            CourseTeacherAssignment.objects.bulk_create(
                [
                    CourseTeacherAssignment(course_id=course_id, teacher=teacher_profile)
                    for course_id in course_ids if course_id not in existing_course_ids
                ],
                ignore_conflicts=True
            )

            messages.success(request, f'✓ Багш "{last_name} {first_name}" амжилттай шинэчлэгдлээ!')
            return redirect('main:teacher_list')
            
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
            courses = Course.objects.all().order_by('level', 'name')
            teacher_course_ids = list(teacher_profile.course_assignments.values_list('course_id', flat=True))
            return render(request, 'main/teacher_update.html', {'teacher': teacher_profile, 'courses': courses, 'teacher_course_ids': teacher_course_ids})
    
    courses = Course.objects.all().order_by('level', 'name')
    teacher_course_ids = list(teacher_profile.course_assignments.values_list('course_id', flat=True))
    return render(request, 'main/teacher_update.html', {'teacher': teacher_profile, 'courses': courses, 'teacher_course_ids': teacher_course_ids})

@login_required
def teacher_delete(request, teacher_id):
    """Багш устгах - Зөвхөн админ"""
    if not request.user.profile.is_admin:
        messages.error(request, 'Танд багш устгах эрх байхгүй байна.')
        return redirect('main:teacher_list')
    
    teacher_profile = get_object_or_404(
        UserProfile, 
        id=teacher_id,
        role__in=[UserRole.TEACHER_BEGINNER, UserRole.TEACHER_INTERMEDIATE, UserRole.TEACHER_ADVANCED]
    )
    
    if request.method == 'POST':
        teacher_name = teacher_profile.mongolian_name or teacher_profile.user.username
        user = teacher_profile.user
        
        try:
            # User устгахад profile автоматаар устана (CASCADE)
            user.delete()
            messages.success(request, f'✓ Багш "{teacher_name}" амжилттай устгагдлаа.')
            return redirect('main:teacher_list')
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
            return redirect('main:teacher_list')
    
    return redirect('main:teacher_list')

@login_required
def enrollment_list(request):
    """Бүртгэлүүдийн жагсаалт - Админ, менежер"""
    profile = request.user.profile
    if not (profile.is_admin or profile.is_manager):
        messages.error(request, 'Хандах эрхгүй байна.')
        return redirect('main:dashboard')
    
    # Бүх enrollments эсвэл зөвхөн PENDING
    status_filter = request.GET.get('status', 'PENDING')
    
    if status_filter == 'ALL':
        enrollments = Enrollment.objects.all()
    else:
        enrollments = Enrollment.objects.filter(status=status_filter)
    
    enrollments = enrollments.select_related('student__user', 'course').order_by('-enrolled_date')
    
    context = {
        'enrollments': enrollments,
        'status_filter': status_filter,
        'pending_count': Enrollment.objects.filter(status='PENDING').count()
    }
    return render(request, 'main/enrollment_list.html', context)

@login_required
def enrollment_approve(request, enrollment_id):
    """Бүртгэл баталгаажуулах - Админ, менежер"""
    profile = request.user.profile
    if not (profile.is_admin or profile.is_manager):
        messages.error(request, 'Хандах эрхгүй байна.')
        return redirect('main:dashboard')
    
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    # Энэ урсгалд баталгаажсан бүртгэлийг төгссөн төлөв рүү шилжүүлнэ.
    enrollment.status = 'COMPLETED'
    enrollment.save()
    
    messages.success(request, f'✓ {enrollment.student.full_name}-ын {enrollment.course.name} бүртгэл батлагдаж "Төгссөн" төлөвт шилжлээ!')
    return redirect('main:enrollment_list')

@login_required
def enrollment_reject(request, enrollment_id):
    """Бүртгэл татгалзах - Админ, менежер"""
    profile = request.user.profile
    if not (profile.is_admin or profile.is_manager):
        messages.error(request, 'Хандах эрхгүй байна.')
        return redirect('main:dashboard')
    
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    enrollment.status = 'CANCELLED'
    enrollment.is_active = False
    enrollment.save()
    
    messages.success(request, f'✗ {enrollment.student.full_name}-ын {enrollment.course.name} бүртгэл цуцлагдлаа.')
    return redirect('main:enrollment_list')

@login_required
def attendance_list(request):
    """Ирц бүртгэх - Багш, менежер, админд харагдана"""
    profile = request.user.profile
    
    # Багш, менежер, админ эрх шалгах
    if not (profile.is_admin or profile.is_manager or profile.is_teacher):
        messages.error(request, 'Танд ирц бүртгэх эрх байхгүй байна.')
        return redirect('main:dashboard')
    
    # Багш бол өөрийн хичээлүүд, менежер/админ бол бүх хичээлүүд
    if profile.is_teacher:
        courses = Course.objects.filter(
            Q(teacher=profile) | Q(teacher_assignments__teacher=profile),
            is_active=True
        ).distinct()
    else:
        courses = Course.objects.filter(is_active=True)
    
    return render(request, 'main/attendance_list.html', {'courses': courses})


@login_required
def attendance_sheet(request, course_id):
    """Ирцийн хуудас - Мөрөөр сурагч, баганаар огноо"""
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    profile = request.user.profile
    
    # Эрх шалгах - Админ, менежер, багш
    if not (profile.is_admin or profile.is_manager or profile.is_teacher):
        messages.error(request, 'Танд ирц бүртгэх эрх байхгүй байна.')
        return redirect('main:dashboard')
    
    # Хичээл авах
    course = get_object_or_404(Course, id=course_id, is_active=True)
    
    # Багш бол зөвхөн өөрийн хичээлийн ирц бүртгэнэ (менежер/админ бол бүх хичээл)
    if profile.is_teacher and not (
        course.teacher_id == profile.id or CourseTeacherAssignment.objects.filter(course=course, teacher=profile).exists()
    ):
        messages.error(request, 'Та зөвхөн өөрийн хичээлийн ирц бүртгэх эрхтэй.')
        return redirect('main:attendance_list')
    
    # Идэвхтэй бүртгэлтэй сурагчид
    enrollments = Enrollment.objects.filter(
        course=course,
        is_active=True,
        status='APPROVED'
    ).select_related('student__user').order_by(
        'student__first_name',
        'student__last_name',
        'student__mongolian_name',
        'student__user__username'
    )

    selected_teachers = UserProfile.objects.filter(
        Q(id=course.teacher_id) | Q(course_assignments__course=course),
        role__in=[
            UserRole.TEACHER_BEGINNER,
            UserRole.TEACHER_INTERMEDIATE,
            UserRole.TEACHER_ADVANCED,
        ]
    ).select_related('user').distinct().order_by('last_name', 'first_name', 'user__username')
    selected_teacher_ids = list(selected_teachers.values_list('id', flat=True))
    
    if request.method == 'POST':
        action = request.POST.get('action', 'save_attendance')

        if action == 'save_template':
            selected_weekdays_raw = request.POST.getlist('weekday_pattern')
            try:
                selected_weekdays = sorted({int(day) for day in selected_weekdays_raw if day.isdigit() and 0 <= int(day) <= 6})
            except (TypeError, ValueError):
                selected_weekdays = []

            if not selected_weekdays:
                messages.error(request, 'Долоо хоногийн дор хаяж 1 гариг сонгоно уу.')
            else:
                template, _ = AttendanceWeekdayTemplate.objects.get_or_create(course=course)
                template.set_weekday_numbers(selected_weekdays)
                template.save()
                messages.success(request, '✓ Ирцийн гаригийн загвар амжилттай хадгалагдлаа!')

            return redirect('main:attendance_sheet', course_id=course_id)

        if action == 'delete_template':
            deleted_count, _ = AttendanceWeekdayTemplate.objects.filter(course=course).delete()
            if deleted_count:
                messages.success(request, '✓ Ирцийн гаригийн загвар устгагдлаа.')
            else:
                messages.info(request, 'Устгах загвар олдсонгүй.')
            return redirect('main:attendance_sheet', course_id=course_id)

        # Ирц хадгалах
        all_dates = set()
        for date_str in request.POST.getlist('visible_dates'):
            try:
                all_dates.add(datetime.strptime(date_str, '%Y-%m-%d').date())
            except ValueError:
                continue

        if not all_dates:
            for key in request.POST.keys():
                if key.startswith('attendance_') or key.startswith('teacher_attendance_'):
                    parts = key.split('_')
                    if len(parts) >= 3:
                        date_str = parts[-1]
                        try:
                            all_dates.add(datetime.strptime(date_str, '%Y-%m-%d').date())
                        except ValueError:
                            continue

        for enrollment in enrollments:
            for date in all_dates:
                checkbox_name = f'attendance_{enrollment.id}_{date.strftime("%Y-%m-%d")}'
                # get_or_create() дараа ашиглаж update хийнэ (update_or_create() IGNORE хийнэ defaults-г)
                attendance, created = Attendance.objects.get_or_create(
                    enrollment=enrollment,
                    date=date,
                    defaults={'present': True, 'notes': ''}
                )
                # Checkbox-н төлөвөөр шинэчлэх
                attendance.present = checkbox_name in request.POST
                attendance.notes = ''
                attendance.save()

        for teacher in selected_teachers:
            for date in all_dates:
                checkbox_name = f'teacher_attendance_{teacher.id}_{date.strftime("%Y-%m-%d")}'
                # get_or_create() дараа ашиглаж update хийнэ (update_or_create() IGNORE хийнэ defaults-г)
                teacher_att, created = TeacherAttendance.objects.get_or_create(
                    course=course,
                    teacher=teacher,
                    date=date,
                    defaults={'present': True, 'notes': ''}
                )
                # Checkbox-н төлөвөөр шинэчлэх
                teacher_att.present = checkbox_name in request.POST
                teacher_att.notes = ''
                teacher_att.save()

        messages.success(request, '✓ Ирц амжилттай хадгалагдлаа!')
        return redirect('main:attendance_sheet', course_id=course_id)
    
    # GET хүсэлт
    # Он/сар шүүлт авах
    from datetime import datetime
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    today = timezone.now().date()
    
    # Эхлээд оны/сарын анхдагч утга нь өнөөдрийн өн/сар
    if not year:
        year = str(today.year)
    if not month:
        month = str(today.month)
    
    # Эхлээд бүх хадгалагдсан ирцийн огноог авах
    all_attendance = Attendance.objects.filter(
        enrollment__in=enrollments
    ).values_list('date', flat=True).distinct().order_by('date')
    
    # Хадгалагдсан огноонуудыг set-д хадгалах
    saved_dates = set(all_attendance)
    
    if year and month:
        # Шүүлтийн дагуу огноо тооцоолох
        try:
            year_int = int(year)
            month_int = int(month)
            start = datetime(year_int, month_int, 1).date()
            # Сарын сүүлийн өдөр
            if month_int == 12:
                end = datetime(year_int + 1, 1, 1).date() - timedelta(days=1)
            else:
                end = datetime(year_int, month_int + 1, 1).date() - timedelta(days=1)
        except:
            # Алдаа гарвал default
            if course.start_date and course.end_date:
                start = course.start_date
                end = min(course.end_date, today)
            else:
                start = today - timedelta(days=30)
                end = today
    elif course.start_date and course.end_date:
        # Course-н хугацааны дагуу
        start = course.start_date
        end = min(course.end_date, today)
    else:
        # Default: Өнөөдрөөс өмнөх 30 хоног
        start = today - timedelta(days=30)
        end = today
    
    template = AttendanceWeekdayTemplate.objects.filter(course=course).first()
    selected_weekdays = template.get_weekday_numbers() if template else []
    selected_weekday_set = set(selected_weekdays)

    # Огнооны жагсаалт үүсгэх - хадгалагдсан болон шүүлтийн огноог нэгтгэх
    from collections import defaultdict
    dates_by_month = defaultdict(list)
    
    # 1. Шүүлтийн хугацааны огноо нэмэх
    current_date = start
    while current_date <= end:
        if selected_weekday_set and current_date.weekday() not in selected_weekday_set:
            current_date += timedelta(days=1)
            continue

        month_key = current_date.strftime('%Y-%m')
        if current_date not in dates_by_month[month_key]:
            dates_by_month[month_key].append(current_date)
        current_date += timedelta(days=1)
    
    # 2. Хадгалагдсан огноонуудыг нэмэх (шүүлтийн хугацаанд байхгүй ч гэсэн)
    for saved_date in saved_dates:
        # Шүүлттэй бол зөвхөн тухайн хугацааны огноог харуулах
        if year and month:
            if saved_date < start or saved_date > end:
                continue

        if selected_weekday_set and saved_date.weekday() not in selected_weekday_set:
            continue
        
        month_key = saved_date.strftime('%Y-%m')
        if saved_date not in dates_by_month[month_key]:
            dates_by_month[month_key].append(saved_date)
    
    # Сар бүрийн огноог эрэмбэлэх
    for month_key in dates_by_month:
        dates_by_month[month_key].sort()
    
    # Эрэмбэлэх
    dates_by_month = dict(sorted(dates_by_month.items()))
    
    # Ирцийн өгөгдлийг nested dictionary-д хадгалах
    attendance_data = {}
    all_attendance_records = Attendance.objects.filter(
        enrollment__in=enrollments
    ).select_related('enrollment')
    
    for att in all_attendance_records:
        if att.enrollment.id not in attendance_data:
            attendance_data[att.enrollment.id] = {}
        attendance_data[att.enrollment.id][att.date] = att.present

    teacher_attendance_data = {}
    if selected_teacher_ids:
        all_teacher_attendance_records = TeacherAttendance.objects.filter(
            course=course,
            teacher_id__in=selected_teacher_ids
        ).select_related('teacher')

        for teacher_attendance in all_teacher_attendance_records:
            if teacher_attendance.teacher.id not in teacher_attendance_data:
                teacher_attendance_data[teacher_attendance.teacher.id] = {}
            teacher_attendance_data[teacher_attendance.teacher.id][teacher_attendance.date] = teacher_attendance.present
    
    # Нийт өдрийн тоо тооцоолох
    total_days = sum(len(dates) for dates in dates_by_month.values())
    
    # Он сонгох жагсаалт
    current_year = today.year
    year_range = range(current_year - 2, current_year + 3)  # Өмнөх 2 он, одоо, дараагийн 2 он
    
    context = {
        'course': course,
        'enrollments': enrollments,
        'dates_by_month': dates_by_month,
        'attendance_data': attendance_data,
        'selected_teacher_ids': selected_teacher_ids,
        'selected_teachers': selected_teachers,
        'teacher_attendance_data': teacher_attendance_data,
        'weekday_options': [
            (0, '1 дэх өдөр (Даваа)'),
            (1, '2 дахь өдөр (Мягмар)'),
            (2, '3 дахь өдөр (Лхагва)'),
            (3, '4 дэх өдөр (Пүрэв)'),
            (4, '5 дахь өдөр (Баасан)'),
            (5, '6 дахь өдөр (Бямба)'),
            (6, '7 дахь өдөр (Ням)'),
        ],
        'selected_weekdays': selected_weekdays,
        'has_weekday_template': bool(template),
        'selected_year': year,
        'selected_month': month,
        'total_days': total_days,
        'year_range': year_range,
    }
    
    return render(request, 'main/attendance_sheet.html', context)


@login_required
def attendance_mark(request, course_id):
    """Тухайн хичээлийн ирц бүртгэх"""
    profile = request.user.profile
    
    # Эрх шалгах - Админ, менежер, багш
    if not (profile.is_admin or profile.is_manager or profile.is_teacher):
        messages.error(request, 'Танд ирц бүртгэх эрх байхгүй байна.')
        return redirect('main:dashboard')
    
    # Хичээл авах
    course = get_object_or_404(Course, id=course_id, is_active=True)
    
    # Багш бол зөвхөн өөрийн хичээлийн ирц бүртгэнэ
    if profile.is_teacher and not (
        course.teacher_id == profile.id or CourseTeacherAssignment.objects.filter(course=course, teacher=profile).exists()
    ):
        messages.error(request, 'Та зөвхөн өөрийн хичээлийн ирц бүртгэх эрхтэй.')
        return redirect('main:attendance_list')
    
    # Идэвхтэй бүртгэлтэй сурагчид
    enrollments = Enrollment.objects.filter(
        course=course, 
        is_active=True,
        status='APPROVED'
    ).select_related('student__user').order_by(
        'student__first_name',
        'student__last_name',
        'student__mongolian_name',
        'student__user__username'
    )
    
    if request.method == 'POST':
        date_str = request.POST.get('date')
        
        if not date_str:
            messages.error(request, 'Огноо сонгоно уу.')
            return render(request, 'main/attendance_mark.html', {
                'course': course,
                'enrollments': enrollments,
            })
        
        try:
            from datetime import datetime
            attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # DEBUG: POST өгөгдлийг харах
            print(f"\n{'='*80}")
            print(f"📅 ИРЦИЙН ӨДӨР: {attendance_date}")
            print(f"📝 POST ӨГӨГДӨЛ:")
            
            # Ирц бүртгэх
            marked_count = 0
            present_count = 0
            absent_count = 0
            
            for enrollment in enrollments:
                is_present = request.POST.get(f'present_{enrollment.id}') == 'on'
                notes = request.POST.get(f'notes_{enrollment.id}', '').strip()
                
                # DEBUG info
                status_icon = "✅" if is_present else "❌"
                print(f"   {status_icon} {enrollment.student.mongolian_name}: present={is_present}, notes='{notes}'")
                
                if is_present:
                    present_count += 1
                else:
                    absent_count += 1
                
                # Ирц үүсгэх эсвэл шинэчлэх (get_or_create() дараа update)
                attendance, created = Attendance.objects.get_or_create(
                    enrollment=enrollment,
                    date=attendance_date,
                    defaults={'present': True, 'notes': ''}
                )
                # Checkbox-н төлөвөөр шинэчлэх
                attendance.present = is_present
                attendance.notes = notes
                attendance.save()
                marked_count += 1
            
            print(f"\n📊 ДҮГНЭЛТ: {marked_count} нийт, {present_count} ирсэн, {absent_count} тасалсан")
            print(f"{'='*80}\n")
            
            messages.success(request, f'✓ {attendance_date} өдрийн {marked_count} сурагчийн ирц амжилттай бүртгэгдлээ!')
            
            # Redirect биш өөрчлөгдсөн өгөгдлийг дахин render хийх (хадгалсан checkbox төлөвийг хадгалахын тулд)
            selected_date = attendance_date
            
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
            selected_date = date.today()
    else:
        # GET request - хамгийн сүүлийн ирцийг харуулах (default огноо болгох)
        latest_attendance = Attendance.objects.filter(
            enrollment__course=course
        ).order_by('-date').first()
        
        default_date = latest_attendance.date if latest_attendance else date.today()
        
        # Өнөөдрийн эсвэл сонгосон өдрийн ирц харуулах
        selected_date_str = request.GET.get('date')
        if selected_date_str:
            try:
                from datetime import datetime
                selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            except:
                selected_date = default_date
        else:
            selected_date = default_date
    
    # Сурагч бүрийн ирцийг авах
    attendance_data = []
    for enrollment in enrollments:
        try:
            attendance = Attendance.objects.get(
                enrollment=enrollment,
                date=selected_date
            )
            attendance_data.append({
                'enrollment': enrollment,
                'present': attendance.present,
                'notes': attendance.notes
            })
        except Attendance.DoesNotExist:
            # Тухайн өдөрт ирц бүртгээгүй бол default "ирсэн" (checkbox checked)
            # Багш нар зөвхөн тасалсан сурагчдын checkbox-г авна
            attendance_data.append({
                'enrollment': enrollment,
                'present': True,  # Default: бүгд ирсэн гэж үзнэ
                'notes': ''
            })
    
    return render(request, 'main/attendance_mark.html', {
        'course': course,
        'attendance_data': attendance_data,
        'selected_date': selected_date,
    })


@login_required
def course_list(request):
    """Сургалтын жагсаалт"""
    courses = Course.objects.all().select_related('teacher__user').order_by('-is_active', '-end_date')
    
    # Админ эрх шалгах
    is_admin = False
    if hasattr(request.user, 'profile'):
        is_admin = request.user.profile.role in [UserRole.PRESIDENT, UserRole.DIRECTOR, UserRole.MANAGER, UserRole.ACCOUNTANT]
    
    return render(request, 'main/course_list.html', {
        'courses': courses,
        'is_admin': is_admin
    })

@login_required
@login_required
def course_create(request):
    """Шинэ хичээл үүсгэх - Админ, менежер, нягтлан"""
    # Эрх шалгах
    if not hasattr(request.user, 'profile') or request.user.profile.role not in [UserRole.PRESIDENT, UserRole.DIRECTOR, UserRole.MANAGER, UserRole.ACCOUNTANT]:
        messages.error(request, 'Танд хичээл үүсгэх эрх байхгүй байна.')
        return redirect('main:course_list')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        level = request.POST.get('level')
        teacher_id = request.POST.get('teacher')
        is_active = request.POST.get('is_active') == 'on'
        
        teachers = UserProfile.objects.filter(
            role__in=[UserRole.TEACHER_BEGINNER, UserRole.TEACHER_INTERMEDIATE, UserRole.TEACHER_ADVANCED]
        ).select_related('user')
        
        # Validation
        if not name:
            messages.error(request, 'Хичээлийн нэр оруулна уу.')
            return render(request, 'main/course_form.html', {'teachers': teachers})
        
        if not level:
            messages.error(request, 'Түвшин сонгоно уу.')
            return render(request, 'main/course_form.html', {'teachers': teachers})
        
        try:
            teacher = UserProfile.objects.get(id=teacher_id) if teacher_id else None
            today = timezone.now().date()
            
            course = Course.objects.create(
                name=name,
                level=level,
                duration_weeks=0,
                price=0,
                start_date=today,
                end_date=today,
                teacher=teacher,
                is_active=is_active
            )
            if teacher:
                CourseTeacherAssignment.objects.get_or_create(course=course, teacher=teacher)
            
            messages.success(request, f'✓ "{name}" сургалт амжилттай үүслээ!')
            return redirect('main:course_list')
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
            return render(request, 'main/course_form.html', {'teachers': teachers})
    
    # Багш нарын жагсаалт
    teachers = UserProfile.objects.filter(
        role__in=[UserRole.TEACHER_BEGINNER, UserRole.TEACHER_INTERMEDIATE, UserRole.TEACHER_ADVANCED]
    ).select_related('user')
    
    return render(request, 'main/course_form.html', {'teachers': teachers})

@login_required
def course_edit(request, course_id):
    """Хичээл засах - Админ, менежер, нягтлан"""
    # Эрх шалгах
    if not hasattr(request.user, 'profile') or request.user.profile.role not in [UserRole.PRESIDENT, UserRole.DIRECTOR, UserRole.MANAGER, UserRole.ACCOUNTANT]:
        messages.error(request, 'Танд хичээл засах эрх байхгүй байна.')
        return redirect('main:course_list')
    
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        messages.error(request, 'Хичээл олдсонгүй.')
        return redirect('main:course_list')
    
    if request.method == 'POST':
        course.name = request.POST.get('name')
        course.level = request.POST.get('level')
        course.duration_weeks = request.POST.get('duration_weeks') or course.duration_weeks
        course.price = request.POST.get('price') or course.price
        course.start_date = request.POST.get('start_date') or course.start_date
        course.end_date = request.POST.get('end_date') or course.end_date
        course.is_active = request.POST.get('is_active') == 'on'
        
        teacher_id = request.POST.get('teacher')
        course.teacher = UserProfile.objects.get(id=teacher_id) if teacher_id else None
        
        course.save()
        if course.teacher:
            CourseTeacherAssignment.objects.get_or_create(course=course, teacher=course.teacher)
        messages.success(request, f'"{course.name}" хичээл амжилттай шинэчлэгдлээ.')
        return redirect('main:course_list')
    
    # Багш нарын жагсаалт
    teachers = UserProfile.objects.filter(
        role__in=[UserRole.TEACHER_BEGINNER, UserRole.TEACHER_INTERMEDIATE, UserRole.TEACHER_ADVANCED]
    ).select_related('user')
    
    return render(request, 'main/course_form.html', {
        'course': course,
        'teachers': teachers
    })

@login_required
def course_delete(request, course_id):
    """Хичээл устгах - Админ, менежер, нягтлан"""
    # Эрх шалгах
    if not hasattr(request.user, 'profile') or request.user.profile.role not in [UserRole.PRESIDENT, UserRole.DIRECTOR, UserRole.MANAGER, UserRole.ACCOUNTANT]:
        messages.error(request, 'Танд хичээл устгах эрх байхгүй байна.')
        return redirect('main:course_list')
    
    try:
        course = Course.objects.get(id=course_id)
        course_name = course.name
        course.is_active = False  # Устгахын оронд идэвхгүй болгох
        course.save()
        messages.success(request, f'"{course_name}" хичээл устгагдлаа.')
    except Course.DoesNotExist:
        messages.error(request, 'Хичээл олдсонгүй.')
    
    return redirect('main:course_list')

def about(request):
    """Танилцуулга хуудас"""
    return render(request, 'main/about.html')

def gotopa_meditation(request):
    """Готопа бясалгал гэж юу вэ?"""
    return render(request, 'main/gotopa_meditation.html')

def guru_gotopa(request):
    """Гүрү Готопа багш"""
    return render(request, 'main/guru_gotopa.html')

def meditation_center(request):
    """Бясалгалын төв"""
    return render(request, 'main/meditation_center.html')

def news(request):
    """Мэдээлэл"""
    return render(request, 'main/news.html')

# Бясалгалын сургалтууд
def courses(request):
    """Бясалгалын сургалтууд"""
    return render(request, 'main/courses.html')

def beginner_meditation(request):
    """Анхан шатны бясалгал"""
    return render(request, 'main/beginner_meditation.html')

def intermediate_meditation(request):
    """Дунд шатны бясалгал"""
    return render(request, 'main/intermediate_meditation.html')

def advanced_meditation(request):
    """Дээд шатны бясалгал"""
    return render(request, 'main/advanced_meditation.html')

def vip_meditation(request):
    """Зуны VIP бясалгал"""
    return render(request, 'main/vip_meditation.html')

# Бүтээгдэхүүн
def products(request):
    """Бүтээгдэхүүн"""
    return render(request, 'main/products.html')

def books(request):
    """Ном"""
    return render(request, 'main/books.html')

def teacher_guidance(request):
    """Багшийн засал"""
    return render(request, 'main/teacher_guidance.html')

def energy_products(request):
    """Энергийн бүтээгдэхүүн"""
    return render(request, 'main/energy_products.html')

def bio_energy_diagnosis(request):
    """Био энергийн оношилгоо"""
    return render(request, 'main/bio_energy_diagnosis.html')

def travel(request):
    """Аялал"""
    return render(request, 'main/travel.html')

def contact(request):
    """Холбоо барих"""
    return render(request, 'main/contact.html')

@require_POST
@login_required
def update_page_content(request):
    """AJAX endpoint - Хуудасны агуулга шинэчлэх (inline editing)"""
    # Зөвхөн Content Editor эрхтэй хэрэглэгч
    if not (request.user.is_superuser or 
            request.user.groups.filter(name='Content Editor').exists()):
        return JsonResponse({
            'success': False,
            'error': 'Танд агуулга засах эрх байхгүй байна.'
        }, status=403)
    
    try:
        key = request.POST.get('key')
        content = request.POST.get('content')
        
        if not key:
            return JsonResponse({
                'success': False,
                'error': 'Түлхүүр (key) шаардлагатай.'
            }, status=400)
        
        # PageContent олж шинэчлэх
        page_content = PageContent.objects.get(key=key)
        page_content.content = content
        page_content.updated_by = request.user
        page_content.save()
        
        return JsonResponse({
            'success': True,
            'message': f'"{page_content.title}" амжилттай шинэчиллээ.',
            'content': page_content.content
        })
        
    except PageContent.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Түлхүүр "{key}" олдсонгүй.'
        }, status=404)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Алдаа гарлаа: {str(e)}'
        }, status=500)


# ========================================
# БАРАА МАТЕРИАЛЫН УДИРДЛАГА
# ========================================

@login_required
def product_set_initial_stock(request):
    """Барааны эхний үлдэгдэл тохируулах"""
    if request.method != 'POST':
        return redirect('main:inventory_list')
    
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах
    has_access = (
        profile.is_admin or 
        profile.role == UserRole.ACCOUNTANT or 
        user.is_superuser or
        user.has_perm('main.change_product')
    )
    if not has_access:
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:inventory_list')
    
    product_id = request.POST.get('product_id')
    initial_stock = request.POST.get('initial_stock')
    note = request.POST.get('note', '')
    
    try:
        product = Product.objects.get(id=product_id)
        old_initial = product.initial_stock
        new_initial = int(initial_stock)
        
        # Эхний үлдэгдэл шинэчлэх
        product.initial_stock = new_initial
        product.save()
        
        messages.success(
            request, 
            f'"{product.name}" барааны эхний үлдэгдэл {old_initial} → {new_initial} болж өөрчлөгдлөө. {note}'
        )
    except Product.DoesNotExist:
        messages.error(request, 'Бараа олдсонгүй.')
    except ValueError:
        messages.error(request, 'Тоо оруулна уу.')
    except Exception as e:
        messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    return redirect('main:inventory_list')


@login_required
def inventory_cost_calculation(request):
    """Дундаж өртгийн (WAC) тооцоолол — бараа тус бүрээр эхний үлдэгдэл, орлого, дундаж өртөг"""
    profile = request.user.profile
    user = request.user

    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.view_product')
    )
    if not has_access:
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')

    products = Product.objects.filter(is_active=True).prefetch_related('movements').order_by('name')

    rows = []
    grand_initial_qty = 0
    grand_initial_value = Decimal('0')
    grand_in_qty = 0
    grand_in_value = Decimal('0')
    grand_current_qty = 0
    grand_avg_value = Decimal('0')

    for product in products:
        init_qty = product.initial_stock or 0
        init_price = product.purchase_price or Decimal('0')
        init_value = init_qty * init_price

        # Орлогын хөдөлгөөнүүд (худалдан авалт, үнэгүй орлого)
        in_movements = [m for m in product.movements.all() if m.movement_type == 'IN']
        in_qty = sum(m.quantity for m in in_movements)
        in_value = sum((m.total_amount or Decimal('0')) for m in in_movements)

        total_qty = init_qty + in_qty
        total_value = init_value + in_value

        avg_cost = (total_value / total_qty) if total_qty > 0 else init_price
        current_qty = product.current_stock
        avg_inventory_value = current_qty * avg_cost

        rows.append({
            'product': product,
            'init_qty': init_qty,
            'init_price': init_price,
            'init_value': init_value,
            'in_qty': in_qty,
            'in_value': in_value,
            'in_movements': in_movements,
            'total_qty': total_qty,
            'total_value': total_value,
            'avg_cost': avg_cost,
            # Дундаж өртөг нь эхний үнээс өөр болсон эсэх (өнгөөр тэмдэглэхэд)
            'price_changed': bool(in_qty) and avg_cost != init_price,
            'current_qty': current_qty,
            'avg_inventory_value': avg_inventory_value,
        })

        grand_initial_qty += init_qty
        grand_initial_value += init_value
        grand_in_qty += in_qty
        grand_in_value += in_value
        grand_current_qty += current_qty
        grand_avg_value += avg_inventory_value

    context = {
        'rows': rows,
        'grand_initial_qty': grand_initial_qty,
        'grand_initial_value': grand_initial_value,
        'grand_in_qty': grand_in_qty,
        'grand_in_value': grand_in_value,
        'grand_current_qty': grand_current_qty,
        'grand_avg_value': grand_avg_value,
    }
    return render(request, 'main/inventory_cost_calculation.html', context)


@login_required
def unlink_bank_transaction(request, transaction_id):
    """Unlink a single bank/cash transaction from any related documents and journal entries."""
    profile = request.user.profile
    user = request.user

    # Permission: admin/accountant/manager or change permission
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.change_banktransaction')
    )

    if not has_access:
        messages.error(request, 'Энэ үйлдэл хийх эрх танд байхгүй.')
        return redirect('main:dashboard')

    transaction = get_object_or_404(BankTransaction, id=transaction_id)

    # Where to return after unlinking: prefer explicit POST/GET `return_to`, then Referer
    return_to = request.POST.get('return_to', request.GET.get('return_to', '')).strip()

    if request.method != 'POST':
        messages.error(request, 'Энэ үйлдлийг POST аргаар дуудаж байх шаардлагатай.')
        return redirect('main:cash_transaction_list')

    try:
        # Detach accounting entry on transaction
        if transaction.accounting_entry:
            ae = transaction.accounting_entry
            transaction.accounting_entry = None
            transaction.is_processed = False
            transaction.save(update_fields=['accounting_entry', 'is_processed'])
            try:
                ae.delete()
            except Exception:
                pass

        # Remove auto-created cash counterpart rows (кассын эсрэг мөр)
        try:
            from .import_bank_transactions import delete_cash_transfer_mirrors
            delete_cash_transfer_mirrors(transaction)
        except Exception:
            pass

        # Remove extra splits' accounting entries (but keep split records)
        try:
            if hasattr(transaction, 'extra_splits'):
                for bts in transaction.extra_splits.all():
                    if bts.accounting_entry:
                        ae2 = bts.accounting_entry
                        bts.accounting_entry = None
                        bts.save(update_fields=['accounting_entry'])
                        try:
                            ae2.delete()
                        except Exception:
                            pass
        except Exception:
            pass

        # Remove student payment allocations
        try:
            PaymentAllocation.objects.filter(transaction=transaction).delete()
        except Exception:
            pass

        # Remove sale payment allocations and legacy sale link
        try:
            SalePaymentAllocation.objects.filter(transaction=transaction).delete()
            if transaction.income_sale_id:
                transaction.income_sale = None
            transaction.is_processed = False
            transaction.save(update_fields=['income_sale', 'is_processed'])
        except Exception:
            pass

        messages.success(request, 'Гүйлгээний холболт амжилттай цуцлагдлаа.')
    except Exception as e:
        messages.error(request, f'Цуцлах явцад алдаа гарлаа: {e}')

    # Try returning to provided return_to (must be local path)
    if return_to and return_to.startswith('/'):
        return redirect(return_to)

    # Fallback to Referer header if available and local
    try:
        from urllib.parse import urlparse
        ref = request.META.get('HTTP_REFERER', '')
        if ref:
            parsed = urlparse(ref)
            ref_path = parsed.path or ''
            if parsed.query:
                ref_path = f"{ref_path}?{parsed.query}"
            if ref_path.startswith('/'):
                return redirect(ref_path)
    except Exception:
        pass

    return redirect('main:cash_transaction_list')


@login_required
def inventory_list(request):
    """Бараа материалын жагсаалт"""
    profile = request.user.profile
    user = request.user
    
    # Админ, нягтлан, эсвэл эрхтэй (permission-based)
    has_access = (
        profile.is_admin or 
        profile.role == UserRole.ACCOUNTANT or 
        user.is_superuser or
        user.has_perm('main.view_product')
    )
    if not has_access:
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    # Хайлт, шүүлт
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    status = request.GET.get('status', '')
    
    products = Product.objects.select_related('category', 'created_by').all()
    
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(code__icontains=query) |
            Q(supplier__icontains=query)
        )
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    if status == 'active':
        products = products.filter(is_active=True)
    elif status == 'inactive':
        products = products.filter(is_active=False)
    elif status == 'low_stock':
        products = [p for p in products if p.is_low_stock]
    
    categories = ProductCategory.objects.filter(is_active=True)
    
    # Статистик
    total_products = products.count() if not status == 'low_stock' else len(products)
    total_stock_value = sum(p.stock_value for p in products)
    low_stock_count = sum(1 for p in Product.objects.all() if p.is_low_stock)
    
    context = {
        'products': products,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
        'selected_status': status,
        'total_products': total_products,
        'total_stock_value': total_stock_value,
        'low_stock_count': low_stock_count,
    }
    
    return render(request, 'main/inventory_list.html', context)


@login_required
def product_create(request):
    """Бараа материал нэмэх"""
    profile = request.user.profile
    user = request.user
    
    has_access = (
        profile.is_admin or 
        profile.role == UserRole.ACCOUNTANT or 
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.add_product') or
        user.has_perm('main.can_manage_inventory')
    )
    if not has_access:
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:inventory_list')
    
    if request.method == 'POST':
        try:
            # Нийлүүлэгч
            supplier_id = request.POST.get('supplier_fk')
            
            product = Product(
                code=request.POST.get('code'),
                name=request.POST.get('name'),
                category_id=request.POST.get('category') if request.POST.get('category') else None,
                description=request.POST.get('description', ''),
                purchase_price=Decimal(request.POST.get('purchase_price', 0)),
                selling_price=Decimal(request.POST.get('selling_price', 0)),
                unit=request.POST.get('unit', 'PIECE'),
                initial_stock=int(request.POST.get('initial_stock', 0)),
                min_stock=int(request.POST.get('min_stock', 0)),
                supplier_fk_id=supplier_id if supplier_id else None,
                supplier=request.POST.get('supplier', ''),
                supplier_contact=request.POST.get('supplier_contact', ''),
                notes=request.POST.get('notes', ''),
                created_by=request.user
            )
            
            if 'image' in request.FILES:
                product.image = request.FILES['image']
            
            product.save()
            messages.success(request, f'Бүтээгдэхүүн "{product.name}" амжилттай нэмэгдлээ.')
            return redirect('main:inventory_list')
            
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    categories = ProductCategory.objects.filter(is_active=True)
    suppliers = Counterparty.objects.filter(
        counterparty_type__in=['SUPPLIER', 'BOTH'],
        is_active=True
    ).order_by('name')
    
    context = {
        'categories': categories,
        'units': Product.UNIT_CHOICES,
        'suppliers': suppliers,
    }
    return render(request, 'main/product_form.html', context)


@login_required
def product_edit(request, product_id):
    """Бараа материал засах"""
    profile = request.user.profile
    user = request.user
    
    has_access = (
        profile.is_admin or 
        profile.role == UserRole.ACCOUNTANT or 
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.change_product') or
        user.has_perm('main.can_manage_inventory')
    )
    if not has_access:
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:inventory_list')
    
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        try:
            # Нийлүүлэгч
            supplier_id = request.POST.get('supplier_fk')
            
            product.code = request.POST.get('code')
            product.name = request.POST.get('name')
            product.category_id = request.POST.get('category') if request.POST.get('category') else None
            product.description = request.POST.get('description', '')
            product.purchase_price = Decimal(request.POST.get('purchase_price', 0))
            product.selling_price = Decimal(request.POST.get('selling_price', 0))
            product.unit = request.POST.get('unit', 'PIECE')
            product.min_stock = int(request.POST.get('min_stock', 0))
            product.supplier_fk_id = supplier_id if supplier_id else None
            product.supplier = request.POST.get('supplier', '')
            product.supplier_contact = request.POST.get('supplier_contact', '')
            product.notes = request.POST.get('notes', '')
            product.is_active = request.POST.get('is_active') == 'on'
            
            if 'image' in request.FILES:
                product.image = request.FILES['image']
            
            product.save()
            messages.success(request, f'Бүтээгдэхүүн "{product.name}" амжилттай шинэчиллээ.')
            return redirect('main:inventory_list')
            
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    categories = ProductCategory.objects.filter(is_active=True)
    suppliers = Counterparty.objects.filter(
        counterparty_type__in=['SUPPLIER', 'BOTH'],
        is_active=True
    ).order_by('name')
    
    context = {
        'product': product,
        'categories': categories,
        'units': Product.UNIT_CHOICES,
        'suppliers': suppliers,
        'is_edit': True,
    }
    return render(request, 'main/product_form.html', context)


@login_required
def stock_movement_create(request):
    """Агуулахын хөдөлгөөн бүртгэх"""
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан бодогч, Менежер бүлэг эсвэл хөдөлгөөн үүсгэх эрхтэй
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.add_stockmovement')
    )
    
    if not has_access:
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:inventory_list')
    
    if request.method == 'POST':
        try:
            product_id = request.POST.get('product')
            product = Product.objects.get(id=product_id)
            
            movement = StockMovement(
                product=product,
                movement_type=request.POST.get('movement_type'),
                quantity=int(request.POST.get('quantity')),
                price=Decimal(request.POST.get('price')),
                reference_number=request.POST.get('reference_number', ''),
                customer_name=request.POST.get('customer_name', ''),
                notes=request.POST.get('notes', ''),
                created_by=request.user
            )
            
            movement.save()
            messages.success(request, f'Хөдөлгөөн амжилттай бүртгэгдлээ. Үлдэгдэл: {product.current_stock}')
            return redirect('main:stock_movement_list')
            
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    products = Product.objects.filter(is_active=True)
    context = {
        'products': products,
        'movement_types': StockMovement.MOVEMENT_TYPE_CHOICES,
    }
    return render(request, 'main/stock_movement_form.html', context)


@login_required
def stock_movement_delete(request, movement_id):
    """Агуулахын хөдөлгөөн устгах (борлуулалттай холбоогүй хөдөлгөөн)"""
    profile = request.user.profile
    user = request.user

    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.delete_stockmovement')
    )
    if not has_access:
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:inventory_list')

    movement = get_object_or_404(StockMovement, id=movement_id)

    # Борлуулалттай холбогдсон хөдөлгөөнийг эндээс устгахгүй — борлуулалтаараа устгана
    if getattr(movement, 'sale_id', None):
        messages.error(
            request,
            'Энэ хөдөлгөөн борлуулалттай холбогдсон байна. Борлуулалтаа устгаснаар хамт устна.'
        )
        return redirect('main:inventory_list')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                product_name = movement.product.name
                # current_stock нь @property тул тусад нь өөрчлөх шаардлагагүй —
                # StockMovement устсаны дараа автоматаар тооцоологдоно.
                movement.delete()

            messages.success(request, f'"{product_name}" барааны хөдөлгөөн амжилттай устгагдлаа.')
            return redirect('main:inventory_list')
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')

    return render(request, 'main/stock_movement_delete_confirm.html', {'movement': movement})


@login_required
def stock_free_intake(request):
    """Үнэгүй орлогодох — 0 үнээр бараа агуулахад оруулах"""
    profile = request.user.profile
    user = request.user
    has_access = (
        profile.is_admin or profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.add_stockmovement')
    )
    if not has_access:
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:inventory_list')

    REASON_CHOICES = [
        ('RETURN',     'Буцаалт — үйлчлүүлэгч буцааж өгсөн'),
        ('GIFT',       'Бэлэг — үнэгүй авсан / хандив'),
        ('SAMPLE',     'Дээж — туршилтын бараа'),
        ('COUNT_ADJ',  'Тооллогын залруулга — засварлах'),
        ('TRANSFER',   'Шилжүүлэг — өөр агуулахаас'),
        ('OTHER',      'Бусад'),
    ]

    if request.method == 'POST':
        intake_date_str = request.POST.get('intake_date', '')
        reason          = request.POST.get('reason', 'OTHER')
        notes           = request.POST.get('notes', '')
        product_ids     = request.POST.getlist('product_id[]')
        quantities      = request.POST.getlist('quantity[]')

        if not product_ids:
            messages.error(request, 'Дор хаяж нэг бараа оруулна уу.')
        else:
            saved = 0
            errors = []
            for pid, qty_str in zip(product_ids, quantities):
                pid = pid.strip().replace(',', '')
                qty_str = qty_str.strip().replace(',', '')
                if not pid or not qty_str:
                    continue
                try:
                    qty = int(qty_str)
                    if qty <= 0:
                        continue
                    product = Product.objects.get(pk=pid)
                    ref = f"FREE-{reason[:3]}-{date.today().strftime('%Y%m%d')}"
                    movement = StockMovement(
                        product=product,
                        movement_type='IN',
                        quantity=qty,
                        price=Decimal('0'),
                        reference_number='',   # auto-generated in save()
                        customer_name='',
                        notes=f"[{reason}] {notes}".strip('[] '),
                        created_by=request.user,
                    )
                    movement.save()
                    saved += 1
                except Product.DoesNotExist:
                    errors.append(f'Бараа #{pid} олдсонгүй.')
                except Exception as e:
                    errors.append(str(e))

            for err in errors:
                messages.error(request, err)
            if saved:
                messages.success(request, f'{saved} барааг амжилттай орлогодлоо.')
                return redirect('main:stock_movement_list')

    products = Product.objects.filter(is_active=True).order_by('name')
    REASON_CHOICES = [
        ('RETURN',    'Буцаалт — үйлчлүүлэгч буцааж өгсөн'),
        ('GIFT',      'Бэлэг — үнэгүй авсан / хандив'),
        ('SAMPLE',    'Дээж — туршилтын бараа'),
        ('COUNT_ADJ', 'Тооллогын залруулга'),
        ('TRANSFER',  'Шилжүүлэг — өөр агуулахаас'),
        ('OTHER',     'Бусад'),
    ]
    context = {
        'products':       products,
        'reason_choices': REASON_CHOICES,
        'today':          date.today().isoformat(),
    }
    return render(request, 'main/stock_free_intake.html', context)


@login_required
def stock_free_outgoing(request):
    """Үнэгүй зарлагадах — 0 үнээр бараа агуулахаас гаргах"""
    profile = request.user.profile
    user = request.user
    has_access = (
        profile.is_admin or profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.add_stockmovement')
    )
    if not has_access:
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:inventory_list')

    REASON_CHOICES = [
        ('WASTE',      'Хаягдал — гэмтсэн / хаягдсан'),
        ('INTERNAL',   'Дотоод хэрэглээ — байгууллагын хэрэгцээнд'),
        ('GIFT_OUT',   'Бэлэг — хандив, бэлэглэл'),
        ('COUNT_ADJ',  'Тооллогын залруулга — илүүдэл засварлах'),
        ('TRANSFER',   'Шилжүүлэг — өөр агуулах руу'),
        ('OTHER',      'Бусад'),
    ]

    if request.method == 'POST':
        reason      = request.POST.get('reason', 'OTHER')
        notes       = request.POST.get('notes', '')
        product_ids = request.POST.getlist('product_id[]')
        quantities  = request.POST.getlist('quantity[]')

        if not product_ids:
            messages.error(request, 'Дор хаяж нэг бараа оруулна уу.')
        else:
            saved = 0
            errors = []
            for pid, qty_str in zip(product_ids, quantities):
                pid = pid.strip().replace(',', '')
                qty_str = qty_str.strip().replace(',', '')
                if not pid or not qty_str:
                    continue
                try:
                    qty = int(qty_str)
                    if qty <= 0:
                        continue
                    product = Product.objects.get(pk=pid)
                    if product.current_stock < qty:
                        errors.append(f'{product.name}: үлдэгдэл хүрэлцэхгүй (үлдэгдэл: {product.current_stock}, хүсэлт: {qty}).')
                        continue
                    movement = StockMovement(
                        product=product,
                        movement_type='OUT',
                        quantity=qty,
                        price=Decimal('0'),
                        reference_number='',
                        customer_name='',
                        notes=f"[{reason}] {notes}".strip('[] '),
                        created_by=request.user,
                    )
                    movement.save()
                    saved += 1
                except Product.DoesNotExist:
                    errors.append(f'Бараа #{pid} олдсонгүй.')
                except Exception as e:
                    errors.append(str(e))

            for err in errors:
                messages.error(request, err)
            if saved:
                messages.success(request, f'{saved} барааг амжилттай зарлагадлаа.')
                return redirect('main:stock_movement_list')

    products = Product.objects.filter(is_active=True).order_by('name')
    context = {
        'products':       products,
        'reason_choices': REASON_CHOICES,
        'today':          date.today().isoformat(),
    }
    return render(request, 'main/stock_free_outgoing.html', context)


@login_required
def stock_movement_list(request):
    """Агуулахын хөдөлгөөний жагсаалт"""
    profile = request.user.profile
    user = request.user
    
    # Админ, нягтлан, эсвэл эрхтэй (permission-based)
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.has_perm('main.view_stockmovement')
    )
    
    if not has_access:
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    movements = StockMovement.objects.select_related('product', 'created_by').order_by('-created_at')[:100]
    
    # Статистик
    total_in = StockMovement.objects.filter(movement_type='IN').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_out = StockMovement.objects.filter(movement_type='OUT').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    context = {
        'movements': movements,
        'total_in': total_in,
        'total_out': total_out,
    }
    return render(request, 'main/stock_movement_list.html', context)


# ========================================
# САНХҮҮГИЙН МОДУЛЬ
# ========================================

@login_required
def finance_dashboard(request):
    """Санхүү, мөнгөн хөрөнгийн хяналт"""
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан эсвэл эрхтэй (Менежерт харуулахгүй!)
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.has_perm('main.view_accountingentry')
    )
    
    if not has_access:
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    # Дансны төлөвлөгөөнөөс мөнгөн хөрөнгийн дансууд (100x, 101x, 110x)
    cash_bank_accounts = ChartOfAccounts.objects.filter(
        is_active=True
    ).filter(
        Q(code__startswith='100') |
        Q(code__startswith='101') |
        Q(code__startswith='110') |
        Q(banktransaction__isnull=False)
    ).distinct().order_by('code')

    account_ids = [acc.id for acc in cash_bank_accounts]
    tx_summary = BankTransaction.objects.filter(
        bank_account_id__in=account_ids
    ).values('bank_account_id').annotate(
        total_income=Sum('income_amount'),
        total_expense=Sum('expense_amount')
    )
    tx_map = {
        row['bank_account_id']: {
            'income': row['total_income'] or Decimal('0'),
            'expense': row['total_expense'] or Decimal('0'),
        }
        for row in tx_summary
    }

    cash_bank_balances = []
    bank_account_balances = []
    total_cash = Decimal('0')
    total_bank = Decimal('0')

    for account in cash_bank_accounts:
        opening_balance = account.opening_balance or Decimal('0')
        total_income = tx_map.get(account.id, {}).get('income', Decimal('0'))
        total_expense = tx_map.get(account.id, {}).get('expense', Decimal('0'))
        closing_balance = opening_balance + total_income - total_expense

        cash_bank_balances.append({
            'account': account,
            'opening_balance': opening_balance,
            'total_income': total_income,
            'total_expense': total_expense,
            'closing_balance': closing_balance,
        })

        if account.code.startswith('110'):
            bank_account_balances.append({
                'account': account,
                'opening_balance': opening_balance,
                'total_income': total_income,
                'total_expense': total_expense,
                'closing_balance': closing_balance,
            })
            total_bank += closing_balance
        elif account.code.startswith('100') or account.code.startswith('101'):
            total_cash += closing_balance

    total_balance = total_cash + total_bank
    
    # Харилцагчдын өр
    suppliers_debt = Counterparty.objects.filter(
        counterparty_type__in=['SUPPLIER', 'BOTH'],
        balance__gt=0
    ).aggregate(Sum('balance'))['balance__sum'] or 0
    
    customers_debt = Counterparty.objects.filter(
        counterparty_type__in=['CUSTOMER', 'BOTH'],
        balance__lt=0
    ).aggregate(Sum('balance'))['balance__sum'] or 0
    
    # Сүүлийн гүйлгээнүүд
    recent_transactions = Transaction.objects.select_related(
        'account', 'counterparty', 'created_by'
    ).order_by('-transaction_date', '-created_at')[:10]
    
    # Сүүлийн худалдан авалт/борлуулалт
    recent_purchases = Purchase.objects.select_related('supplier').order_by('-purchase_date')[:5]
    recent_sales = Sale.objects.select_related('customer').order_by('-sale_date')[:5]

    # Банкны гүйлгээний статистик
    bank_transactions = BankTransaction.objects.filter(account_type='BANK')
    bank_tx_total = bank_transactions.count()
    bank_tx_linked = bank_transactions.filter(is_processed=True).count()
    bank_tx_unlinked = bank_transactions.filter(is_processed=False).count()
    
    context = {
        'cash_bank_balances': cash_bank_balances,
        'bank_account_balances': bank_account_balances,
        'total_cash': total_cash,
        'total_bank': total_bank,
        'total_balance': total_balance,
        'suppliers_debt': suppliers_debt,
        'customers_debt': abs(customers_debt),
        'recent_transactions': recent_transactions,
        'recent_purchases': recent_purchases,
        'recent_sales': recent_sales,
        'bank_tx_total': bank_tx_total,
        'bank_tx_linked': bank_tx_linked,
        'bank_tx_unlinked': bank_tx_unlinked,
        'cash_bank_total_closing': sum(item['closing_balance'] for item in cash_bank_balances),
    }
    
    return render(request, 'main/finance_dashboard.html', context)


@login_required
def account_opening_balance(request):
    """Дансны эхний үлдэгдэл оруулах"""
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан бодогч, Менежер бүлэг эсвэл эхний үлдэгдэл засах эрхтэй
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.change_chartofaccounts')
    )
    
    if not has_access:
        messages.error(request, 'Танд эхний үлдэгдэл оруулах эрх байхгүй.')
        return redirect('main:finance_dashboard')
    
    if request.method == 'POST':
        try:
            updated_count = 0
            
            # Бүх дансны эхний үлдэгдлийг шинэчлэх
            accounts = ChartOfAccounts.objects.filter(is_active=True)
            
            for account in accounts:
                opening_key = f'opening_{account.id}'
                
                if opening_key in request.POST:
                    opening_value = request.POST.get(opening_key, '0')
                    
                    try:
                        opening = Decimal(opening_value) if opening_value else Decimal('0')
                        
                        # Үлдэгдэл өөрчлөгдсөн эсэхийг шалгах
                        if account.opening_balance != opening:
                            account.opening_balance = opening
                            account.save()
                            updated_count += 1
                    except (ValueError, TypeError):
                        continue
            
            if updated_count > 0:
                messages.success(request, f'✓ {updated_count} дансны эхний үлдэгдэл амжилттай хадгалагдлаа!')
            else:
                messages.info(request, 'Өөрчлөлт олдсонгүй.')
            
            return redirect('main:account_opening_balance')
            
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
            return redirect('main:account_opening_balance')
    
    # GET хүсэлт - бүх дансыг харуулах
    accounts = ChartOfAccounts.objects.filter(is_active=True).order_by('code')
    
    context = {
        'accounts': accounts,
    }
    
    return render(request, 'main/account_opening_balance.html', context)


@login_required
def purchase_list(request):
    """Худалдан авалтын жагсаалт - StockMovement (movement_type='IN')"""
    profile = request.user.profile
    user = request.user
    
    has_access = (
        profile.is_admin or 
        profile.role == UserRole.ACCOUNTANT or 
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.view_stockmovement')
    )
    if not has_access:
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    # StockMovement-н худалдан авалтууд (movement_type='IN')
    purchases = StockMovement.objects.filter(movement_type='IN').select_related(
        'product', 'counterparty', 'bank_account', 'created_by'
    )
    
    # Шүүлтүүд
    supplier = request.GET.get('supplier', '')
    if supplier:
        purchases = purchases.filter(counterparty__name__icontains=supplier)
    
    payment_method = request.GET.get('payment_method', '')
    if payment_method:
        purchases = purchases.filter(payment_method=payment_method)
    
    date_from = request.GET.get('date_from', '')
    if date_from:
        purchases = purchases.filter(created_at__gte=date_from)
    
    date_to = request.GET.get('date_to', '')
    if date_to:
        purchases = purchases.filter(created_at__lte=date_to)
    
    # Статистик
    total_quantity = purchases.aggregate(total=Sum('quantity'))['total'] or 0
    total_amount = purchases.aggregate(total=Sum('total_amount'))['total'] or 0
    
    context = {
        'purchases': purchases.order_by('-created_at')[:100],  # Сүүлийн 100
        'total_quantity': total_quantity,
        'total_amount': total_amount,
        'payment_methods': StockMovement.PAYMENT_METHOD_CHOICES,
        'selected_payment_method': payment_method,
    }
    
    return render(request, 'main/purchase_list.html', context)


@login_required
@login_required
def sale_list(request):
    """Борлуулалтын жагсаалт - Sale загвараас"""
    profile = request.user.profile
    user = request.user

    has_access = (
        profile.is_admin or
        profile.role == UserRole.ACCOUNTANT or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.view_stockmovement')
    )
    if not has_access:
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')

    sales = Sale.objects.select_related(
        'customer', 'payment_account', 'created_by'
    ).prefetch_related('items__product', 'banktransaction_set', 'payment_allocations__transaction')

    # Шүүлтүүд
    customer = request.GET.get('customer', '').strip()
    if customer:
        sales = sales.filter(Q(customer__name__icontains=customer))

    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        sales = sales.filter(status=status_filter)

    payment_method_filter = request.GET.get('payment_method', '').strip()
    # backward compatibility: хуучин `pay_type` query key-г дэмжинэ
    if not payment_method_filter:
        legacy_pay_type = request.GET.get('pay_type', '').strip()
        legacy_map = {
            'Касс': 'CASH',
            'Харилцах': 'BANK',
            'Зээлээр': 'CREDIT',
            'Касс + Харилцах': 'BOTH',
        }
        payment_method_filter = legacy_map.get(legacy_pay_type, '')

    if payment_method_filter == 'CASH':
        sales = sales.filter(expected_payment_method__icontains='Касс').exclude(
            expected_payment_method__icontains='Харилцах'
        )
    elif payment_method_filter == 'BANK':
        sales = sales.filter(expected_payment_method__icontains='Харилцах').exclude(
            expected_payment_method__icontains='Касс'
        )
    elif payment_method_filter == 'CREDIT':
        sales = sales.filter(expected_payment_method__icontains='Зээлээр')
    elif payment_method_filter == 'BOTH':
        sales = sales.filter(
            Q(expected_payment_method__icontains='Касс') &
            Q(expected_payment_method__icontains='Харилцах')
        )

    date_from = request.GET.get('date_from', '').strip()
    if date_from:
        sales = sales.filter(sale_date__gte=date_from)

    date_to = request.GET.get('date_to', '').strip()
    if date_to:
        sales = sales.filter(sale_date__lte=date_to)

    salesperson = request.GET.get('salesperson', '').strip()
    if salesperson:
        sales = sales.filter(salesperson_name__icontains=salesperson)

    bank_link_filter = request.GET.get('bank_link', '').strip()
    if bank_link_filter == 'LINKED':
        sales = sales.filter(
            Q(banktransaction__isnull=False) | Q(payment_allocations__isnull=False)
        ).distinct()
    elif bank_link_filter == 'UNLINKED':
        sales = sales.exclude(
            Q(banktransaction__isnull=False) | Q(payment_allocations__isnull=False)
        ).distinct()

    sales = sales.order_by('-sale_date', '-created_at')

    # Нийт статистик (шүүлтүүрийн дараа, хуудаслалтын өмнө)
    total_amount   = sales.aggregate(total=Sum('total_amount'))['total'] or 0
    total_count    = sales.count()
    legacy_linked_ids = set(sales.filter(banktransaction__isnull=False).values_list('id', flat=True).distinct())
    allocation_linked_ids = set(
        SalePaymentAllocation.objects.filter(sale__in=sales).values_list('sale_id', flat=True).distinct()
    )
    linked_count = len(legacy_linked_ids.union(allocation_linked_ids))
    unlinked_count = total_count - linked_count

    # Хуудаслалт — нэг хуудсанд 50 мөр
    per_page = int(request.GET.get('per_page', 50))
    if per_page not in (25, 50, 100, 200):
        per_page = 50
    paginator   = Paginator(sales, per_page)
    page_number = request.GET.get('page', 1)
    page_obj    = paginator.get_page(page_number)

    # Одоогийн хуудасны нийт дүн
    page_amount = sum(s.total_amount for s in page_obj.object_list)

    # Шүүлтүүрийн GET параметрүүдийг урагш дамжуулах (page-г хассан)
    filter_params = request.GET.copy()
    filter_params.pop('page', None)

    context = {
        'page_obj':        page_obj,
        'paginator':       paginator,
        'total_amount':    total_amount,
        'total_count':     total_count,
        'linked_count':    linked_count,
        'unlinked_count':  unlinked_count,
        'page_amount':     page_amount,
        'per_page':        per_page,
        'filter_params':   filter_params.urlencode(),
        'status_choices':  Sale.STATUS_CHOICES,
        'selected_status':     status_filter,
        'selected_payment_method': payment_method_filter,
        'selected_bank_link': bank_link_filter,
        'selected_salesperson': salesperson,
    }
    return render(request, 'main/sale_list.html', context)


@login_required
def sale_detail(request, sale_id):
    """Борлуулалтын дэлгэрэнгүй"""
    profile = request.user.profile
    user = request.user
    has_access = (
        profile.is_admin or profile.role == UserRole.ACCOUNTANT or
        user.is_superuser or user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.view_stockmovement')
    )
    if not has_access:
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')

    sale = get_object_or_404(
        Sale.objects.select_related('customer', 'payment_account', 'created_by')
            .prefetch_related('items__product', 'banktransaction_set'),
        pk=sale_id
    )

    def get_tx_available_for_sale(tx_obj):
        """Тухайн гүйлгээнээс энэ борлуулалтад холбож болох үлдэгдэл дүн"""
        student_alloc = tx_obj.allocations.aggregate(s=Sum('amount'))['s'] or Decimal('0')
        other_sales_alloc = tx_obj.sale_allocations.exclude(sale=sale).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        same_sale_alloc = tx_obj.sale_allocations.filter(sale=sale).aggregate(s=Sum('amount'))['s'] or Decimal('0')

        # Legacy бүрэн холбоос өөр борлуулалт руу заасан бол энэ борлуулалтад холбох боломжгүй
        if tx_obj.income_sale_id and tx_obj.income_sale_id != sale.id and tx_obj.sale_allocations.count() == 0:
            return Decimal('0')

        max_for_this_sale = tx_obj.income_amount - student_alloc - other_sales_alloc
        if max_for_this_sale < 0:
            max_for_this_sale = Decimal('0')

        # Одоогийн борлуулалтад өмнө нь холбосон дүнгээ засах боломж олгоно
        available = max_for_this_sale if same_sale_alloc == 0 else max_for_this_sale
        return available if available > 0 else Decimal('0')

    # Холбох боломжтой гүйлгээнүүд — бүх төрлийн, аль хэдийн cold борлуулалттай холбогдсоныг хасна.
    # Мөн шууд дансанд (эсрэг данс / журналын бичилт) холбогдсон гүйлгээг хасна —
    # жишээ нь "Хандивийн орлого" болгож ангилсан гүйлгээг борлуулалтад дахин холбож болохгүй.
    # Борлуулалтад хэсэгчлэн хуваарилагдсан гүйлгээ бол үлдэгдлээ холбох боломжтой хэвээр байна.
    available_txs = BankTransaction.objects.filter(
        income_amount__gt=0,
    ).exclude(
        income_sale__isnull=False
    ).annotate(
        has_sale_alloc=Exists(
            SalePaymentAllocation.objects.filter(transaction=OuterRef('pk'))
        )
    ).exclude(
        Q(has_sale_alloc=False) &
        (Q(offset_account__isnull=False) | Q(accounting_entry__isnull=False))
    ).select_related('bank_account', 'counterparty').order_by('-transaction_date')

    # Хайлтын параметрүүд
    q_desc      = request.GET.get('q_desc', '').strip()
    q_date_from = request.GET.get('q_date_from', '').strip()
    q_date_to   = request.GET.get('q_date_to', '').strip()
    q_amount    = request.GET.get('q_amount', '').strip()
    q_actype    = request.GET.get('q_actype', '').strip()   # BANK | CASH
    q_txtype    = request.GET.get('q_txtype', '').strip()   # income | expense | all
    return_to   = request.GET.get('return_to', '').strip()
    if return_to and not return_to.startswith('/'):
        return_to = ''

    if q_desc:
        available_txs = available_txs.filter(
            Q(description__icontains=q_desc) | Q(counterparty_name__icontains=q_desc)
        )
    if q_date_from:
        available_txs = available_txs.filter(transaction_date__gte=q_date_from)
    if q_date_to:
        available_txs = available_txs.filter(transaction_date__lte=q_date_to)
    if q_amount:
        try:
            amt = Decimal(q_amount.replace(',', ''))
            available_txs = available_txs.filter(
                Q(income_amount__gte=amt * Decimal('0.9'),
                  income_amount__lte=amt * Decimal('1.1')) |
                Q(expense_amount__gte=amt * Decimal('0.9'),
                  expense_amount__lte=amt * Decimal('1.1'))
            )
        except Exception:
            pass
    if q_actype:
        available_txs = available_txs.filter(account_type=q_actype)
    if q_txtype == 'income':
        available_txs = available_txs.filter(income_amount__gt=0)
    elif q_txtype == 'expense':
        available_txs = available_txs.filter(expense_amount__gt=0)

    # Хайлт хийгдээгүй үед борлуулалтын огноо орчмын гүйлгээг санал болгох
    show_all = any([q_desc, q_date_from, q_date_to, q_amount, q_actype, q_txtype])
    if not show_all:
        if sale.sale_date:
            from datetime import timedelta
            d = sale.sale_date
            available_txs = available_txs.filter(
                transaction_date__gte=d - timedelta(days=7),
                transaction_date__lte=d + timedelta(days=7),
            )

    # Хуваарилах үлдэгдэл дүнгүй гүйлгээнүүдийг жагсаалтаас хасах
    available_tx_list = []
    for tx in available_txs:
        tx.available_for_link = get_tx_available_for_sale(tx)
        if tx.available_for_link > 0:
            available_tx_list.append(tx)

    # Холбогдсон гүйлгээнүүд (partial болон legacy full link хоёуланг харуулна)
    linked_allocations = list(
        SalePaymentAllocation.objects.filter(sale=sale)
        .select_related('transaction')
        .order_by('-transaction__transaction_date', '-id')
    )
    linked_txs = []
    for alloc in linked_allocations:
        tx = alloc.transaction
        tx.linked_amount = alloc.amount
        tx.is_partial_link = True
        linked_txs.append(tx)

    legacy_txs = sale.banktransaction_set.exclude(sale_allocations__isnull=False).order_by('-transaction_date', '-id')
    for tx in legacy_txs:
        tx.linked_amount = tx.income_amount
        tx.is_partial_link = False
        linked_txs.append(tx)

    linked_txs.sort(key=lambda x: (x.transaction_date, x.id), reverse=True)

    # Гүйлгээний жагсаалтыг хуудаслалттай болгох
    tx_per_page = 20
    tx_paginator = Paginator(available_tx_list, tx_per_page)
    tx_page_number = request.GET.get('tx_page', 1)
    tx_page_obj = tx_paginator.get_page(tx_page_number)

    tx_filter_params = request.GET.copy()
    tx_filter_params.pop('tx_page', None)

    # Дотоод хэрэгцээний зардлын данс сонгох dropdown-д (7xxx - үйл ажиллагааны зардал)
    expense_accounts = ChartOfAccounts.objects.filter(
        code__startswith='7', is_active=True
    ).order_by('code')

    context = {
        'sale':             sale,
        'linked_txs':       linked_txs,
        'tx_page_obj':      tx_page_obj,
        'tx_paginator':     tx_paginator,
        'tx_filter_params': tx_filter_params.urlencode(),
        'tx_page_number':   tx_page_obj.number,
        'show_all':         show_all,
        'q_desc':           q_desc,
        'q_date_from':      q_date_from,
        'q_date_to':        q_date_to,
        'q_amount':         q_amount,
        'q_actype':         q_actype,
        'q_txtype':         q_txtype,
        'return_to':        return_to,
        'expense_accounts': expense_accounts,
    }
    return render(request, 'main/sale_detail.html', context)


@login_required
def sale_link_bank(request, sale_id):
    """Борлуулалтад банкны гүйлгээ холбох / таслах (POST)"""
    if request.method != 'POST':
        return redirect('main:sale_detail', sale_id=sale_id)
    sale = get_object_or_404(Sale, pk=sale_id)
    tx_id  = request.POST.get('transaction_id', '').replace(',', '').strip()
    action = request.POST.get('action', 'link')  # link | unlink
    redirect_to_return = request.POST.get('redirect_to_return') == '1'

    # Хайлтын параметрүүдийг хадгалж буцах
    qs_params = {
        k: request.POST.get(k, '')
        for k in ['q_desc', 'q_date_from', 'q_date_to', 'q_amount', 'q_actype', 'q_txtype', 'tx_page']
        if request.POST.get(k, '')
    }
    return_to = request.POST.get('return_to', '').strip()
    is_safe_local_return = return_to.startswith('/') and not return_to.startswith('//')

    # Жагсаалтаас таслах үед шууд буцаах боломж
    if redirect_to_return and is_safe_local_return:
        redirect_url = return_to
    else:
        if is_safe_local_return:
            qs_params['return_to'] = return_to

        redirect_url = reverse('main:sale_detail', args=[sale_id])
        if qs_params:
            redirect_url += '?' + urlencode(qs_params)

    if tx_id == '' or not tx_id.isdigit():
        messages.error(request, 'Гүйлгээний дугаар буруу байна.')
        return redirect(redirect_url)

    tx_id_int = int(tx_id)

    if action == 'unlink':
        linked_to_sale = (
            BankTransaction.objects.filter(pk=tx_id_int, income_sale=sale).exists() or
            SalePaymentAllocation.objects.filter(transaction_id=tx_id_int, sale=sale).exists()
        )
        if not linked_to_sale:
            messages.error(request, f'Гүйлгээ #{tx_id} энэ борлуулалттай холбогдоогүй байна.')
            return redirect(redirect_url)

    try:
        tx = BankTransaction.objects.get(pk=tx_id_int)
        if action == 'unlink':
            SalePaymentAllocation.objects.filter(transaction=tx, sale=sale).delete()
            if tx.income_sale_id == sale.id:
                tx.income_sale = None
                tx.save(update_fields=['income_sale'])
            messages.success(request, f'Гүйлгээ #{tx_id} холбоос тасарлаа.')
        else:
            # Шууд дансанд (эсрэг данс / журнал) холбогдсон гүйлгээг борлуулалтад холбохгүй
            already_classified = tx.offset_account_id or tx.accounting_entry_id
            if already_classified and not tx.sale_allocations.exists():
                acct = tx.offset_account
                acct_label = f'"{acct.code} - {acct.name}" данс' if acct else 'журналын бичилт'
                messages.error(
                    request,
                    f'Гүйлгээ #{tx_id} аль хэдийн {acct_label}-тай холбогдсон байна. '
                    f'Эхлээд банк/кассын гүйлгээний хуудаснаас тэр холболтыг цуцалж, дараа нь борлуулалтад холбоно уу.'
                )
                return redirect(redirect_url)

            amount_raw = request.POST.get('link_amount', '').replace(',', '').strip()
            if amount_raw:
                try:
                    link_amount = Decimal(amount_raw)
                except Exception:
                    messages.error(request, 'Холбох дүн буруу байна.')
                    return redirect(redirect_url)
            else:
                link_amount = tx.income_amount

            if link_amount <= 0:
                messages.error(request, 'Холбох дүн 0-ээс их байх ёстой.')
                return redirect(redirect_url)

            student_alloc = tx.allocations.aggregate(s=Sum('amount'))['s'] or Decimal('0')
            other_sales_alloc = tx.sale_allocations.exclude(sale=sale).aggregate(s=Sum('amount'))['s'] or Decimal('0')
            max_for_this_sale = tx.income_amount - student_alloc - other_sales_alloc

            if max_for_this_sale <= 0:
                messages.error(request, 'Энэ гүйлгээний дүн бүрэн хуваарилагдсан байна.')
                return redirect(redirect_url)

            if link_amount > max_for_this_sale:
                messages.error(
                    request,
                    f'Холбох дүн хэтэрсэн байна. Боломжит дүн: {max_for_this_sale:,.0f}₮'
                )
                return redirect(redirect_url)

            # Борлуулалтын НИЙТ дүнгээс хэтрэхээс хамгаалах
            paid_legacy_other = BankTransaction.objects.filter(
                income_sale=sale
            ).exclude(
                sale_allocations__isnull=False
            ).exclude(
                pk=tx.pk
            ).aggregate(s=Sum('income_amount'))['s'] or Decimal('0')

            paid_alloc_other = SalePaymentAllocation.objects.filter(
                sale=sale
            ).exclude(
                transaction=tx
            ).aggregate(s=Sum('amount'))['s'] or Decimal('0')

            max_by_sale_total = sale.total_amount - (paid_legacy_other + paid_alloc_other)
            if max_by_sale_total <= 0:
                messages.error(request, 'Энэ борлуулалтын төлбөр бүрэн холбогдсон байна.')
                return redirect(redirect_url)

            if link_amount > max_by_sale_total:
                messages.error(
                    request,
                    f'Борлуулалтын нийт дүнгээс хэтэрлээ. Энэ борлуулалтад нэмээд {max_by_sale_total:,.0f}₮ хүртэл холбож болно.'
                )
                return redirect(redirect_url)

            # Partial/full allocation байдлаар хадгалах
            SalePaymentAllocation.objects.update_or_create(
                transaction=tx,
                sale=sale,
                defaults={'amount': link_amount}
            )

            # Давхар тооцооллоос сэргийлж legacy income_sale холбоосыг цэвэрлэнэ
            if tx.income_sale_id == sale.id:
                tx.income_sale = None

            if not tx.income_type:
                tx.income_type = 'PRODUCT_SALE'
            tx.save(update_fields=['income_sale', 'income_type'])
            messages.success(request, f'Гүйлгээ #{tx_id} - {link_amount:,.0f}₮ амжилттай холбогдлоо.')

        # Хуваарилалтын бодит төлөвт тулгуурлан ангиллыг дахин тэнцүүлнэ
        student_alloc = tx.allocations.aggregate(s=Sum('amount'))['s'] or Decimal('0')
        sale_alloc = tx.sale_allocations.aggregate(s=Sum('amount'))['s'] or Decimal('0')

        update_fields = []
        if student_alloc > 0 and sale_alloc == 0:
            if tx.income_type != 'STUDENT_PAYMENT':
                tx.income_type = 'STUDENT_PAYMENT'
                update_fields.append('income_type')
            if tx.income_sale_id is not None:
                tx.income_sale = None
                update_fields.append('income_sale')
        elif sale_alloc > 0 and student_alloc == 0:
            if tx.income_type != 'PRODUCT_SALE':
                tx.income_type = 'PRODUCT_SALE'
                update_fields.append('income_type')
            if tx.income_student_id is not None:
                tx.income_student = None
                update_fields.append('income_student')
            if tx.income_course_id is not None:
                tx.income_course = None
                update_fields.append('income_course')
            if tx.income_month is not None:
                tx.income_month = None
                update_fields.append('income_month')
            if tx.income_year is not None:
                tx.income_year = None
                update_fields.append('income_year')
        elif student_alloc > 0 and sale_alloc > 0:
            if tx.income_type != 'STUDENT_PAYMENT':
                tx.income_type = 'STUDENT_PAYMENT'
                update_fields.append('income_type')
            if tx.income_student_id is not None:
                tx.income_student = None
                update_fields.append('income_student')
            if tx.income_course_id is not None:
                tx.income_course = None
                update_fields.append('income_course')
            if tx.income_month is not None:
                tx.income_month = None
                update_fields.append('income_month')
            if tx.income_year is not None:
                tx.income_year = None
                update_fields.append('income_year')
            if tx.income_sale_id is not None:
                tx.income_sale = None
                update_fields.append('income_sale')
        else:
            if tx.income_type is not None:
                tx.income_type = None
                update_fields.append('income_type')
            if tx.income_student_id is not None:
                tx.income_student = None
                update_fields.append('income_student')
            if tx.income_course_id is not None:
                tx.income_course = None
                update_fields.append('income_course')
            if tx.income_month is not None:
                tx.income_month = None
                update_fields.append('income_month')
            if tx.income_year is not None:
                tx.income_year = None
                update_fields.append('income_year')
            if tx.income_sale_id is not None:
                tx.income_sale = None
                update_fields.append('income_sale')

        if update_fields:
            tx.save(update_fields=update_fields)

        # Борлуулалтын орлогын журнал (Дт банк/касс — Кт 510101) болон эсрэг дансыг тэнцүүлэх
        from .import_bank_transactions import sync_sale_revenue_journal
        try:
            journal_result = sync_sale_revenue_journal(tx, request.user)
            if journal_result == 'created':
                messages.info(
                    request,
                    f'Журналын бичилт үүслээ: {tx.accounting_entry.entry_number} '
                    f'(Дт {tx.bank_account.code} / Кт {tx.offset_account.code} {tx.offset_account.name})'
                )
            elif journal_result == 'deleted':
                messages.info(request, 'Холбоос тасарсан тул орлогын журналын бичилт устгагдлаа.')
        except Exception as e:
            messages.warning(request, f'Журналын бичилт үүсгэхэд алдаа гарлаа: {e}')

        # Аль ч тохиолдолд paid_amount дахин тооцоолох (legacy + partial allocation)
        paid_legacy = BankTransaction.objects.filter(
            income_sale=sale
        ).exclude(
            sale_allocations__isnull=False
        ).aggregate(s=Sum('income_amount'))['s'] or Decimal('0')
        paid_alloc = SalePaymentAllocation.objects.filter(sale=sale).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        paid = paid_legacy + paid_alloc
        sale.paid_amount = paid
        if paid >= sale.total_amount and sale.status == 'DRAFT':
            sale.status = 'PAID'
            messages.info(request, f'Борлуулалт "{sale.sale_number}" бүрэн төлөгдсөн болж PAID болов.')
        elif paid < sale.total_amount and sale.status == 'PAID':
            sale.status = 'DRAFT'
        sale.save()
    except BankTransaction.DoesNotExist:
        messages.error(request, f'Гүйлгээ #{tx_id} олдсонгүй.')

    return redirect(redirect_url)


@login_required
def sale_link_expense(request, sale_id):
    """Дотоод хэрэгцээний борлуулалтыг зардлын дансанд холбох / холболтыг цуцлах

    Бичилт: Дебит = сонгосон зардлын данс (5xxx), Кредит = 510101 Борлуулалтын орлого.
    """
    profile = request.user.profile
    user = request.user

    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.change_sale')
    )
    if not has_access:
        messages.error(request, 'Энэ үйлдэл хийх эрх танд байхгүй.')
        return redirect('main:sale_list')

    sale = get_object_or_404(Sale, pk=sale_id)

    return_to = request.POST.get('return_to', '').strip()
    if return_to and (not return_to.startswith('/') or return_to.startswith('//')):
        return_to = ''
    back_url = return_to or reverse('main:sale_detail', args=[sale.id])

    if request.method != 'POST':
        return redirect(back_url)

    action = request.POST.get('action', '').strip()

    try:
        if action == 'unlink':
            if sale.expense_accounting_entry_id:
                entry = sale.expense_accounting_entry
                sale.expense_accounting_entry = None
                sale.save(update_fields=['expense_accounting_entry'])
                entry.delete()
                messages.success(request, 'Зардлын журналын бичилт цуцлагдлаа.')
            else:
                messages.error(request, 'Энэ борлуулалтад холбогдсон зардлын бичилт олдсонгүй.')
            return redirect(back_url)

        if action != 'link':
            messages.error(request, 'Үйлдэл танигдсангүй.')
            return redirect(back_url)

        expense_account_id = request.POST.get('expense_account')
        if not expense_account_id:
            messages.error(request, 'Зардлын данс сонгоно уу.')
            return redirect(back_url)

        expense_account = ChartOfAccounts.objects.filter(id=expense_account_id).first()
        if not expense_account:
            messages.error(request, 'Сонгосон данс олдсонгүй.')
            return redirect(back_url)

        revenue_account = ChartOfAccounts.objects.filter(code='510101').first()
        if not revenue_account:
            messages.error(request, '510101 "Борлуулалтын орлого" данс дансны төлөвлөгөөнд байхгүй байна.')
            return redirect(back_url)

        amount = sale.total_amount or Decimal('0')
        if amount <= 0:
            messages.error(request, 'Борлуулалтын дүн 0 байна — бичилт үүсгэх боломжгүй.')
            return redirect(back_url)

        from .import_bank_transactions import create_accounting_entry_safe, next_entry_number

        # Дахин холбох бол хуучин бичилтийг устгана
        if sale.expense_accounting_entry_id:
            old_entry = sale.expense_accounting_entry
            sale.expense_accounting_entry = None
            sale.save(update_fields=['expense_accounting_entry'])
            old_entry.delete()

        date_key = sale.sale_date.strftime('%Y%m%d')
        _, entry_number = next_entry_number(f'EXP{date_key}')

        entry = create_accounting_entry_safe(
            entry_date=sale.sale_date,
            entry_number=entry_number,
            description=f'Дотоод хэрэгцээ: {sale.sale_number}',
            debit_account=expense_account,
            debit_amount=amount,
            credit_account=revenue_account,
            credit_amount=amount,
            created_by=user,
            related_sale=sale,
        )

        sale.expense_accounting_entry = entry
        sale.save(update_fields=['expense_accounting_entry'])

        messages.success(
            request,
            f'✓ "{expense_account.code} - {expense_account.name}" зардлын дансанд холбогдож, '
            f'журналын бичилт {entry.entry_number} үүслээ.'
        )
    except Exception as e:
        messages.error(request, f'Алдаа гарлаа: {e}')

    return redirect(back_url)


@login_required
def sale_finance_edit(request, sale_id):
    """Борлуулалтын мэдээллийг засах (finance/sales хэсгийн Sale загвар)"""
    profile = request.user.profile
    user = request.user
    has_access = (
        profile.is_admin or
        profile.role == UserRole.ACCOUNTANT or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists()
    )
    if not has_access:
        messages.error(request, 'Энэ борлуулалтыг засах эрх танд байхгүй.')
        return redirect('main:sale_list')

    sale = get_object_or_404(Sale, pk=sale_id)

    if request.method == 'POST':
        with transaction.atomic():
            sale_date = request.POST.get('sale_date', '').strip()
            customer_id = request.POST.get('customer_id', '').strip()
            status = request.POST.get('status', '').strip()
            salesperson_name = request.POST.get('salesperson_name', '').strip()
            expected_payment_method = request.POST.get('expected_payment_method', '').strip()
            notes = request.POST.get('notes', '').strip()

            if sale_date:
                sale.sale_date = sale_date
            if customer_id:
                try:
                    sale.customer = Counterparty.objects.get(pk=int(customer_id))
                except (Counterparty.DoesNotExist, ValueError):
                    sale.customer = None
            else:
                sale.customer = None
            if status in dict(Sale.STATUS_CHOICES):
                sale.status = status
            sale.salesperson_name = salesperson_name
            sale.expected_payment_method = expected_payment_method
            sale.notes = notes

            # ── Бараануудыг шинэчлэх ──────────────────────────────────────
            from main.models import SaleItem
            items = sale.items.all()
            for item in items:
                product_id = request.POST.get(f'item_{item.id}_product', '').strip()
                qty_raw    = request.POST.get(f'item_{item.id}_qty', '').strip()
                price_raw  = request.POST.get(f'item_{item.id}_price', '').strip()

                if product_id and qty_raw and price_raw:
                    try:
                        product = Product.objects.get(pk=int(product_id))
                        qty   = int(qty_raw)
                        price = Decimal(price_raw.replace(',', ''))
                        if qty > 0 and price >= 0:
                            item.product    = product
                            item.quantity   = qty
                            item.unit_price = price
                            item.save()   # total_price auto-calc by model.save()
                    except (Product.DoesNotExist, ValueError, Exception):
                        pass  # буруу утга орвол бараар хэвээр үлдэнэ

            # Нийт дүнг дахин тооцоолох
            sale.total_amount = sale.items.aggregate(s=Sum('total_price'))['s'] or Decimal('0')
            sale.save()

        messages.success(request, f'"{sale.sale_number}" борлуулалтын мэдээлэл амжилттай шинэчлэгдлээ.')
        return redirect('main:sale_detail', sale_id=sale.id)

    customers = Counterparty.objects.filter(
        counterparty_type__in=['CUSTOMER', 'BOTH'], is_active=True
    ).order_by('name')
    products = Product.objects.filter(is_active=True).order_by('name')

    context = {
        'sale': sale,
        'customers': customers,
        'status_choices': Sale.STATUS_CHOICES,
        'products': products,
    }
    return render(request, 'main/sale_finance_edit.html', context)


@login_required
def sale_finance_delete(request, sale_id):
    """Санхүүгийн борлуулалтыг устгах (жагсаалтаас)"""
    profile = request.user.profile
    user = request.user
    has_access = (
        profile.is_admin or
        profile.role == UserRole.ACCOUNTANT or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists()
    )
    if not has_access:
        messages.error(request, 'Энэ борлуулалтыг устгах эрх танд байхгүй.')
        return redirect('main:sale_list')

    if request.method != 'POST':
        messages.error(request, 'Буруу хүсэлт байна.')
        return redirect('main:sale_list')

    sale = get_object_or_404(Sale, pk=sale_id)
    sale_number = sale.sale_number

    return_to = request.POST.get('return_to', '').strip()
    is_safe_local_return = return_to.startswith('/') and not return_to.startswith('//')

    # Устгалын өмнө холбоотой банкны гүйлгээнүүдийг хадгалж аваад,
    # устгалын дараа ангиллыг бодит төлөвт синк хийнэ.
    linked_tx_ids = set(
        sale.payment_allocations.values_list('transaction_id', flat=True)
    )
    linked_tx_ids.update(
        BankTransaction.objects.filter(income_sale=sale).values_list('id', flat=True)
    )

    with transaction.atomic():
        SalePaymentAllocation.objects.filter(sale=sale).delete()
        BankTransaction.objects.filter(income_sale=sale).update(income_sale=None)
        sale.delete()

        for tx in BankTransaction.objects.filter(id__in=linked_tx_ids):
            student_alloc = tx.allocations.aggregate(s=Sum('amount'))['s'] or Decimal('0')
            sale_alloc = tx.sale_allocations.aggregate(s=Sum('amount'))['s'] or Decimal('0')
            update_fields = []

            if student_alloc > 0 and sale_alloc == 0:
                if tx.income_type != 'STUDENT_PAYMENT':
                    tx.income_type = 'STUDENT_PAYMENT'
                    update_fields.append('income_type')
                if tx.income_sale_id is not None:
                    tx.income_sale = None
                    update_fields.append('income_sale')
            elif sale_alloc > 0 and student_alloc == 0:
                if tx.income_type != 'PRODUCT_SALE':
                    tx.income_type = 'PRODUCT_SALE'
                    update_fields.append('income_type')
                if tx.income_student_id is not None:
                    tx.income_student = None
                    update_fields.append('income_student')
                if tx.income_course_id is not None:
                    tx.income_course = None
                    update_fields.append('income_course')
                if tx.income_month is not None:
                    tx.income_month = None
                    update_fields.append('income_month')
                if tx.income_year is not None:
                    tx.income_year = None
                    update_fields.append('income_year')
            elif student_alloc > 0 and sale_alloc > 0:
                if tx.income_type != 'STUDENT_PAYMENT':
                    tx.income_type = 'STUDENT_PAYMENT'
                    update_fields.append('income_type')
                if tx.income_student_id is not None:
                    tx.income_student = None
                    update_fields.append('income_student')
                if tx.income_course_id is not None:
                    tx.income_course = None
                    update_fields.append('income_course')
                if tx.income_month is not None:
                    tx.income_month = None
                    update_fields.append('income_month')
                if tx.income_year is not None:
                    tx.income_year = None
                    update_fields.append('income_year')
                if tx.income_sale_id is not None:
                    tx.income_sale = None
                    update_fields.append('income_sale')
            else:
                if tx.income_type is not None:
                    tx.income_type = None
                    update_fields.append('income_type')
                if tx.income_student_id is not None:
                    tx.income_student = None
                    update_fields.append('income_student')
                if tx.income_course_id is not None:
                    tx.income_course = None
                    update_fields.append('income_course')
                if tx.income_month is not None:
                    tx.income_month = None
                    update_fields.append('income_month')
                if tx.income_year is not None:
                    tx.income_year = None
                    update_fields.append('income_year')
                if tx.income_sale_id is not None:
                    tx.income_sale = None
                    update_fields.append('income_sale')

            if update_fields:
                tx.save(update_fields=update_fields)

    messages.success(request, f'"{sale_number}" борлуулалт амжилттай устгагдлаа.')
    if is_safe_local_return:
        return redirect(return_to)
    return redirect('main:sale_list')


@login_required
def transaction_list(request):
    """Гүйлгээний жагсаалт"""
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан бодогч, Менежер бүлэг эсвэл гүйлгээ харах эрхтэй
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.view_banktransaction')
    )
    
    if not has_access:
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    transactions = Transaction.objects.select_related(
        'account', 'to_account', 'counterparty', 'created_by'
    ).order_by('-transaction_date', '-created_at')
    
    # Шүүлт
    transaction_type = request.GET.get('type', '')
    account_id = request.GET.get('account', '')
    
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    if account_id:
        transactions = transactions.filter(Q(account_id=account_id) | Q(to_account_id=account_id))
    
    # Статистик
    total_income = transactions.filter(transaction_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = transactions.filter(transaction_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0
    
    accounts = Account.objects.filter(is_active=True)
    
    context = {
        'transactions': transactions[:100],  # Сүүлийн 100
        'total_income': total_income,
        'total_expense': total_expense,
        'accounts': accounts,
        'selected_type': transaction_type,
        'selected_account': account_id,
        'transaction_types': Transaction.TRANSACTION_TYPE_CHOICES,
    }
    
    return render(request, 'main/transaction_list.html', context)


@login_required
def import_counterparties_view(request):
    """Харилцагчдыг Excel файлаас импортлох"""
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан бодогч, Менежер бүлэг эсвэл харилцагч импорт эрхтэй
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.add_counterparty')
    )
    
    if not has_access:
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        
        # Файлын өргөтгөл шалгах
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            messages.error(request, 'Зөвхөн Excel файл (.xlsx, .xls) оруулна уу.')
            return redirect('main:import_counterparties')
        
        # Файлыг түр хадгалах
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            for chunk in excel_file.chunks():
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name
        
        try:
            # Импортлох
            result = import_counterparties(tmp_file_path)
            
            if result:
                messages.success(
                    request, 
                    f'Амжилттай импортлолоо! Шинээр үүссэн: {result["created"]}, '
                    f'Шинэчилсэн: {result["updated"]}, Алдаа: {result["errors"]}'
                )
            else:
                messages.error(request, 'Импортлолт амжилтгүй боллоо. Файлын формат шалгана уу.')
        
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
        
        finally:
            # Түр файл устгах
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
        
        return redirect('main:import_counterparties')
    
    # Одоо байгаа харилцагчид
    counterparties = Counterparty.objects.all().order_by('-created_at')[:20]
    
    context = {
        'counterparties': counterparties,
        'total_counterparties': Counterparty.objects.count(),
    }
    
    return render(request, 'main/import_counterparties.html', context)


@login_required
def import_bank_transactions_view(request):
    """Банкны хуулгын файлаас гүйлгээ импортлох"""
    print("\n" + "="*80)
    print(f"🔵 IMPORT VIEW ДУУДАГДЛАА!")
    print(f"Method: {request.method}")
    print(f"POST data: {request.POST}")
    print(f"FILES: {request.FILES}")
    print("="*80 + "\n")
    
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан бодогч, Менежер бүлэг эсвэл банкны гүйлгээ импорт эрхтэй
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.add_banktransaction')
    )
    
    if not has_access:
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    if request.method == 'POST' and request.FILES.get('excel_file'):
        print("🟢 POST + FILE олдлоо, импорт эхэллээ...")
        excel_file = request.FILES['excel_file']
        bank_account_id = request.POST.get('account')  # Template дээрх name="account"
        
        if not bank_account_id:
            print("❌ Account ID хоосон!")
            messages.error(request, 'Банкны данс сонгоно уу.')
            return redirect('main:import_bank_transactions')
        
        # Банкны дансыг авах
        try:
            bank_account = ChartOfAccounts.objects.get(id=bank_account_id)
        except ChartOfAccounts.DoesNotExist:
            messages.error(request, 'Банкны данс олдсонгүй.')
            return redirect('main:import_bank_transactions')
        
        # Файлын өргөтгөл шалгах
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            messages.error(request, 'Зөвхөн Excel файл (.xlsx, .xls) оруулна уу.')
            return redirect('main:import_bank_transactions')
        
        # Файлыг түр хадгалах
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            for chunk in excel_file.chunks():
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name
        
        try:
            # import_bank_transactions автоматаар форматыг таньж авна
            from .import_bank_transactions import import_bank_transactions
            
            print(f"📤 Импорт эхлүүлж байна: {bank_account.code} - {bank_account.name}")
            result = import_bank_transactions(tmp_file_path, bank_account)
            
            if result:
                print(f"✅ Импорт амжилттай: {result}")
                skipped_msg = f', Давхардсан (алгассан): {result["skipped"]}' if result["skipped"] > 0 else ''
                messages.success(
                    request, 
                    f'✓ Амжилттай импортлолоо!\n'
                    f'Банкны данс: {bank_account.code} - {bank_account.name}\n'
                    f'Үүссэн гүйлгээ: {result["created"]}{skipped_msg}, '
                    f'Дансны үлдэгдэл: {result["final_balance"]:,.0f}₮'
                )
                # Амжилттай импортлосон бол гүйлгээний жагсаалт руу
                return redirect('main:bank_transaction_list')
            else:
                print("❌ Импорт амжилтгүй")
                messages.error(request, 'Импортлолт амжилтгүй боллоо. Файлын формат шалгана уу.')
        
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
        
        finally:
            # Түр файл устгах
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
        
        return redirect('main:import_bank_transactions')
    
    # Банкны дансууд (110101 - Харилцах дахь бэлэн мөнгө, 110201 - Банкин дахь валют)
    bank_accounts = ChartOfAccounts.objects.filter(
        is_active=True,
        code__startswith='110'  # Банкны дансууд
    ).order_by('code')
    
    # Хуучин Account системийн дансууд (хэрэв байгаа бол)
    old_accounts = Account.objects.filter(is_active=True).order_by('name')
    
    # Сүүлийн гүйлгээнүүд
    recent_transactions = Transaction.objects.select_related('account', 'counterparty').order_by('-created_at')[:20]
    
    context = {
        'bank_accounts': bank_accounts,
        'old_accounts': old_accounts,
        'recent_transactions': recent_transactions,
        'total_transactions': Transaction.objects.count(),
    }
    
    return render(request, 'main/import_bank_transactions.html', context)


# ========================================
# ЕРӨНХИЙ ЖУРНАЛ
# ========================================

@login_required
def journal_list(request):
    """Ерөнхий журналын жагсаалт - бүх AccountingEntry-үүд"""
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан, менежер эсвэл эрхтэй (permission-based)
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        profile.role == 'MANAGER' or  # Менежер роль
        user.is_superuser or
        user.has_perm('main.view_accountingentry')
    )
    
    if not has_access:
        messages.error(
            request, 
            'Ерөнхий журнал харах эрх танд байхгүй.'
        )
        return redirect('main:finance_dashboard')
    
    # BankTransactionSplit модель байхгүй байж болно (migration-аар устгагдсан)
    try:
        from .models import BankTransactionSplit
    except Exception:
        BankTransactionSplit = None

    prefetch_paths = [
        'banktransaction_set__income_sale__customer',
        'banktransaction_set__sale_allocations__sale__customer',
        'banktransaction_set__allocations__student',
        'banktransaction_set__allocations__course',
        'expense_sales',
    ]
    if BankTransactionSplit:
        prefetch_paths.append('banktransaction_set__extra_splits__account')

    entries = AccountingEntry.objects.select_related(
        'debit_account', 'credit_account', 'created_by'
    ).prefetch_related(*prefetch_paths)

    if BankTransactionSplit:
        # Нэмэлт хуваарилалтын entry-г дангаар харуулахгүй
        entries = entries.filter(split_source__isnull=True)

    entries = entries.order_by('-entry_date', '-entry_number')

    # Хайлт
    search = request.GET.get('search', '')
    if search:
        entries = entries.filter(
            Q(entry_number__icontains=search) |
            Q(description__icontains=search) |
            Q(debit_account__name__icontains=search) |
            Q(credit_account__name__icontains=search)
        )

    # Огноогоор шүүлт
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        entries = entries.filter(entry_date__gte=date_from)
    if date_to:
        entries = entries.filter(entry_date__lte=date_to)

    # Дебит/Кредит дансаар шүүх
    debit_account_id = request.GET.get('debit_account', '')
    credit_account_id = request.GET.get('credit_account', '')
    if debit_account_id:
        entries = entries.filter(debit_account_id=debit_account_id)
    if credit_account_id:
        entries = entries.filter(credit_account_id=credit_account_id)

    # Харилцсан дансны бүлгээс дарахад дансны кодоор шүүх
    debit_prefix = request.GET.get('debit_prefix', '').strip()
    credit_prefix = request.GET.get('credit_prefix', '').strip()
    if debit_prefix:
        entries = entries.filter(debit_account__code__startswith=debit_prefix)
    if credit_prefix:
        entries = entries.filter(credit_account__code__startswith=credit_prefix)

    # Үүсгэсэн хэрэглэгчээр шүүх
    created_by_id = request.GET.get('created_by', '')
    if created_by_id:
        entries = entries.filter(created_by_id=created_by_id)

    # Банкны гүйлгээний дугаараар шүүх
    bank_transaction_id = request.GET.get('bank_transaction_id', '').strip()
    if bank_transaction_id.isdigit():
        entries = entries.filter(
            Exists(BankTransaction.objects.filter(
                accounting_entry=OuterRef('pk'), pk=int(bank_transaction_id)
            ))
        )

    # Банк/кассын гүйлгээтэй холбогдсон эсэхээр шүүх
    linked_status = request.GET.get('linked_status', '')
    has_tx = Exists(BankTransaction.objects.filter(accounting_entry=OuterRef('pk')))
    if linked_status == 'linked':
        entries = entries.filter(has_tx)
    elif linked_status == 'unlinked':
        entries = entries.filter(~has_tx)

    # Статистик
    total_entries = entries.count()
    total_debit = entries.aggregate(Sum('debit_amount'))['debit_amount__sum'] or 0
    total_credit = entries.aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0

    # Харилцсан дансаар (Дебит → Кредит) бүлэглэсэн статистик
    pair_groups = list(
        entries.order_by().values(
            'debit_account__code', 'debit_account__name',
            'credit_account__code', 'credit_account__name',
        ).annotate(cnt=Count('id')).order_by('-cnt')
    )
    grouped_total = sum(p['cnt'] for p in pair_groups)

    # Шүүлтийн dropdown-д зөвхөн журналд хэрэглэгдсэн дансууд/хэрэглэгчид
    debit_accounts = ChartOfAccounts.objects.filter(
        id__in=AccountingEntry.objects.values('debit_account_id')
    ).order_by('code')
    credit_accounts = ChartOfAccounts.objects.filter(
        id__in=AccountingEntry.objects.values('credit_account_id')
    ).order_by('code')
    creators = User.objects.filter(
        id__in=AccountingEntry.objects.values('created_by_id')
    ).order_by('username')

    # Хуудаслалт
    paginator = Paginator(entries, 50)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Мөр тус бүрд холбогдсон баримтын шуурхай холбоос
    for entry in page_obj:
        txs = list(entry.banktransaction_set.all())
        entry.first_tx = txs[0].id if txs else None

        related_sale_id = None
        for tx in txs:
            if tx.income_sale_id:
                related_sale_id = tx.income_sale_id
                break
            sale_allocs = list(tx.sale_allocations.all())
            if sale_allocs:
                related_sale_id = sale_allocs[0].sale_id
                break
        if related_sale_id is None:
            expense_sale = entry.expense_sales.first()
            related_sale_id = expense_sale.id if expense_sale else None
        entry.related_sale_id = related_sale_id

    context = {
        'entries': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': page_obj.has_other_pages(),
        'total_entries': total_entries,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'pair_groups': pair_groups,
        'grouped_total': grouped_total,
        'grouped_total_equals': grouped_total == total_entries,
        'debit_accounts': debit_accounts,
        'credit_accounts': credit_accounts,
        'creators': creators,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
        'debit_account_id': debit_account_id,
        'credit_account_id': credit_account_id,
        'created_by_id': created_by_id,
        'bank_transaction_id': bank_transaction_id,
        'linked_status': linked_status,
        'debit_prefix': debit_prefix,
        'credit_prefix': credit_prefix,
    }

    return render(request, 'main/journal_list.html', context)


@login_required
def journal_create(request):
    """Шинэ журналын бичилт үүсгэх"""
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан бодогч, Менежер бүлэг эсвэл журнал үүсгэх эрхтэй
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.add_accountingentry')
    )
    
    if not has_access:
        messages.error(
            request, 
            'Журналын бичилт үүсгэх эрх танд байхгүй.'
        )
        return redirect('main:journal_list')
    
    if request.method == 'POST':
        entry_number = request.POST.get('entry_number')
        entry_date = request.POST.get('entry_date')
        debit_account_id = request.POST.get('debit_account')
        credit_account_id = request.POST.get('credit_account')
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        
        try:
            debit_account = ChartOfAccounts.objects.get(id=debit_account_id)
            credit_account = ChartOfAccounts.objects.get(id=credit_account_id)
            
            # Журналын бичилт үүсгэх
            entry = AccountingEntry.objects.create(
                entry_number=entry_number,
                entry_date=entry_date,
                debit_account=debit_account,
                credit_account=credit_account,
                debit_amount=amount,
                credit_amount=amount,
                description=description,
                created_by=request.user
            )
            
            messages.success(request, f'Журналын бичилт {entry_number} амжилттай үүслээ.')
            return redirect('main:journal_list')
            
        except ChartOfAccounts.DoesNotExist:
            messages.error(request, 'Данс олдсонгүй.')
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    # Бүх идэвхтэй дансуудыг авах
    accounts = ChartOfAccounts.objects.filter(is_active=True).order_by('code')
    
    # Дараагийн гүйлгээний дугаар
    last_entry = AccountingEntry.objects.order_by('-entry_number').first()
    if last_entry and last_entry.entry_number:
        try:
            last_number = int(last_entry.entry_number.replace('JE', ''))
            next_number = f'JE{last_number + 1:05d}'
        except:
            next_number = f'JE{timezone.now().strftime("%Y%m%d")}001'
    else:
        next_number = f'JE{timezone.now().strftime("%Y%m%d")}001'
    
    context = {
        'accounts': accounts,
        'next_number': next_number,
        'today': timezone.now().date(),
    }
    
    return render(request, 'main/journal_create.html', context)


@login_required
def journal_delete(request, entry_id):
    """Журналын бичилт устгах"""
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан бодогч, Менежер бүлэг эсвэл журнал устгах эрхтэй
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.delete_accountingentry')
    )
    
    if not has_access:
        messages.error(request, 'Журналын бичилт устгах эрх танд байхгүй.')
        return redirect('main:journal_list')
    
    entry = get_object_or_404(AccountingEntry, id=entry_id)
    
    if request.method == 'POST':
        entry_number = entry.entry_number
        entry.delete()
        messages.success(request, f'Журналын бичилт {entry_number} устгагдлаа.')
        return redirect('main:journal_list')

    return redirect('main:journal_list')


@login_required
def journal_unlink_transactions(request, entry_id):
    """Журналын бичилтээс холбогдсон гүйлгээ/баримтуудыг салгах (бичилт өөрөө үлдэнэ)"""
    profile = request.user.profile
    user = request.user

    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.change_accountingentry')
    )

    if not has_access:
        messages.error(request, 'Энэ үйлдэл хийх эрх танд байхгүй.')
        return redirect('main:journal_list')

    entry = get_object_or_404(AccountingEntry, id=entry_id)

    return_to = request.POST.get('return_to', request.GET.get('return_to', '')).strip()
    if return_to and (not return_to.startswith('/') or return_to.startswith('//')):
        return_to = ''
    back_url = return_to or reverse('main:journal_list')

    if request.method != 'POST':
        messages.error(request, 'Энэ үйлдлийг POST аргаар дуудаж байх шаардлагатай.')
        return redirect(back_url)

    detached = 0
    try:
        # Банк/кассын гүйлгээнүүдээс салгах
        for tx in BankTransaction.objects.filter(accounting_entry=entry):
            tx.accounting_entry = None
            tx.is_processed = False
            tx.save(update_fields=['accounting_entry', 'is_processed'])
            detached += 1
            # Автоматаар үүссэн кассын эсрэг мөрүүдийг мөн устгах
            try:
                from .import_bank_transactions import delete_cash_transfer_mirrors
                delete_cash_transfer_mirrors(tx)
            except Exception:
                pass

        # Нэмэлт хуваарилалтуудаас салгах
        try:
            from .models import BankTransactionSplit
            for split in BankTransactionSplit.objects.filter(accounting_entry=entry):
                split.accounting_entry = None
                split.save(update_fields=['accounting_entry'])
                detached += 1
        except Exception:
            pass

        # Дотоод хэрэгцээний зардлын холбоосоос салгах
        for sale in Sale.objects.filter(expense_accounting_entry=entry):
            sale.expense_accounting_entry = None
            sale.save(update_fields=['expense_accounting_entry'])
            detached += 1

        if detached:
            messages.success(
                request,
                f'Журналын бичилт {entry.entry_number}-с {detached} холбоос салгагдлаа.'
            )
        else:
            messages.info(request, f'{entry.entry_number} бичилтэд холбогдсон гүйлгээ олдсонгүй.')
    except Exception as e:
        messages.error(request, f'Салгах явцад алдаа гарлаа: {e}')

    return redirect(back_url)


@login_required
def chart_of_accounts_list(request):
    """Дансны төлөвлөгөө харах"""
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан бодогч, Менежер бүлэг эсвэл дансны төлөвлөгөө харах эрхтэй
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.view_chartofaccounts')
    )
    
    if not has_access:
        messages.error(
            request, 
            'Дансны төлөвлөгөө харах эрх танд байхгүй.'
        )
        return redirect('main:finance_dashboard')
    
    # Бүх дансууд
    accounts = ChartOfAccounts.objects.filter(is_active=True).order_by('code')
    
    # Хайлт
    search = request.GET.get('search', '')
    if search:
        accounts = accounts.filter(
            Q(code__icontains=search) |
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Төрлөөр шүүлт
    account_type = request.GET.get('type', '')
    if account_type:
        accounts = accounts.filter(account_type=account_type)
    
    # Статистик
    stats = {
        'total': ChartOfAccounts.objects.filter(is_active=True).count(),
        'asset': ChartOfAccounts.objects.filter(is_active=True, account_type='ASSET').count(),
        'liability': ChartOfAccounts.objects.filter(is_active=True, account_type='LIABILITY').count(),
        'equity': ChartOfAccounts.objects.filter(is_active=True, account_type='EQUITY').count(),
        'income': ChartOfAccounts.objects.filter(is_active=True, account_type='INCOME').count(),
        'expense': ChartOfAccounts.objects.filter(is_active=True, account_type='EXPENSE').count(),
        'cost': ChartOfAccounts.objects.filter(is_active=True, account_type='COST').count(),
    }
    
    context = {
        'accounts': accounts,
        'stats': stats,
        'search': search,
        'account_type': account_type,
        'is_only_accountant': request.user.profile.is_only_accountant if hasattr(request.user, 'profile') else False,
    }
    
    return render(request, 'main/chart_of_accounts_list.html', context)


@login_required
def chart_account_create(request):
    """Шинэ данс үүсгэх"""
    # Нягтлан бодогчийн эрх шалгах
    if not request.user.profile.is_accountant:
        messages.error(request, 'Данс үүсгэх эрх танд байхгүй.')
        return redirect('main:chart_of_accounts_list')
    
    if request.method == 'POST':
        code = request.POST.get('code')
        name = request.POST.get('name')
        account_type = request.POST.get('account_type')
        parent_id = request.POST.get('parent')
        description = request.POST.get('description', '')
        
        # Validation
        if ChartOfAccounts.objects.filter(code=code).exists():
            messages.error(request, f'Данс код {code} аль хэдийн байна.')
        else:
            parent = None
            if parent_id:
                parent = ChartOfAccounts.objects.get(id=parent_id)
            
            ChartOfAccounts.objects.create(
                code=code,
                name=name,
                account_type=account_type,
                parent=parent,
                description=description
            )
            messages.success(request, f'Данс {code} - {name} амжилттай үүслээ.')
            return redirect('main:chart_of_accounts_list')
    
    # Parent accounts for dropdown
    parents = ChartOfAccounts.objects.filter(is_active=True).order_by('code')
    
    context = {
        'parents': parents,
        'account_types': ChartOfAccounts.ACCOUNT_TYPE_CHOICES,
    }
    
    return render(request, 'main/chart_account_form.html', context)


@login_required
def chart_account_edit(request, account_id):
    """Данс засах"""
    # Нягтлан бодогчийн эрх шалгах
    if not request.user.profile.is_accountant:
        messages.error(request, 'Данс засах эрх танд байхгүй.')
        return redirect('main:chart_of_accounts_list')
    
    account = get_object_or_404(ChartOfAccounts, id=account_id)
    
    if request.method == 'POST':
        account.code = request.POST.get('code')
        account.name = request.POST.get('name')
        account.account_type = request.POST.get('account_type')
        parent_id = request.POST.get('parent')
        account.description = request.POST.get('description', '')
        
        if parent_id:
            account.parent = ChartOfAccounts.objects.get(id=parent_id)
        else:
            account.parent = None
        
        account.save()
        messages.success(request, f'Данс {account.code} - {account.name} амжилттай шинэчлэгдлээ.')
        return redirect('main:chart_of_accounts_list')
    
    # Parent accounts for dropdown (exclude self)
    parents = ChartOfAccounts.objects.filter(is_active=True).exclude(id=account_id).order_by('code')
    
    context = {
        'account': account,
        'parents': parents,
        'account_types': ChartOfAccounts.ACCOUNT_TYPE_CHOICES,
    }
    
    return render(request, 'main/chart_account_form.html', context)


@login_required
def chart_account_delete(request, account_id):
    """Данс устгах"""
    # Нягтлан бодогчийн эрх шалгах
    if not request.user.profile.is_accountant:
        messages.error(request, 'Данс устгах эрх танд байхгүй.')
        return redirect('main:chart_of_accounts_list')
    
    account = get_object_or_404(ChartOfAccounts, id=account_id)
    
    # Check if account has entries
    has_debit_entries = AccountingEntry.objects.filter(debit_account=account).exists()
    has_credit_entries = AccountingEntry.objects.filter(credit_account=account).exists()
    
    if has_debit_entries or has_credit_entries:
        messages.error(
            request, 
            f'Данс {account.code} - {account.name} дээр гүйлгээ хийгдсэн байна. Устгах боломжгүй.'
        )
    else:
        account_name = f'{account.code} - {account.name}'
        account.delete()
        messages.success(request, f'Данс {account_name} амжилттай устгагдлаа.')
    
    return redirect('main:chart_of_accounts_list')


@login_required
def chart_account_delete_empty(request):
    """Хоосон (үлдэгдэлгүй, гүйлгээгүй) дансуудыг бөөнөөр устгах"""
    if not request.user.profile.is_accountant:
        messages.error(request, 'Данс устгах эрх танд байхгүй.')
        return redirect('main:chart_of_accounts_list')

    if request.method != 'POST':
        return redirect('main:chart_of_accounts_list')

    # Аль дансанд AccountingEntry, BankTransaction холбоос байхгүй, бүх үлдэгдэл нь 0 байгааг олох
    candidates = ChartOfAccounts.objects.exclude(
        id__in=AccountingEntry.objects.values_list('debit_account_id', flat=True)
    ).exclude(
        id__in=AccountingEntry.objects.values_list('credit_account_id', flat=True)
    ).exclude(
        id__in=BankTransaction.objects.values_list('bank_account_id', flat=True)
    ).exclude(
        id__in=BankTransaction.objects.filter(
            offset_account__isnull=False
        ).values_list('offset_account_id', flat=True)
    ).filter(
        opening_balance=0,
        debit_balance=0,
        credit_balance=0,
    )

    deleted_names = []
    skipped = 0
    for account in list(candidates):
        try:
            with transaction.atomic():
                name = f'{account.code} - {account.name}'
                account.delete()
                deleted_names.append(name)
        except Exception:
            # ProtectedError гэх мэт — өөр хүснэгтээс хамааралтай данс
            skipped += 1

    if deleted_names:
        messages.success(
            request,
            f'{len(deleted_names)} хоосон данс устгагдлаа: ' + ', '.join(deleted_names[:10]) +
            ('…' if len(deleted_names) > 10 else '')
        )
    else:
        messages.info(request, 'Устгах боломжтой хоосон данс олдсонгүй.')

    if skipped:
        messages.warning(request, f'{skipped} данс өөр бүртгэлтэй холбоотой тул устгагдсангүй.')

    return redirect('main:chart_of_accounts_list')


@login_required
def get_bank_accounts_api(request):
    """Банкны төрлөөс хамааран данснуудыг JSON-аар буцаах"""
    from django.http import JsonResponse
    
    bank_type = request.GET.get('bank_type', '')
    
    # 101x банкны данснуудыг авах (төрөл харгалзахгүй бүгдийг харуулах)
    accounts = ChartOfAccounts.objects.filter(
        code__startswith='101',
        is_active=True
    ).order_by('code')
    
    # JSON format
    data = [
        {
            'id': acc.id,
            'code': acc.code,
            'name': acc.name,
            'balance': float(acc.balance) if acc.balance else 0
        }
        for acc in accounts
    ]
    
    return JsonResponse({'accounts': data, 'count': len(data)})


# ========================================
# БАНКНЫ ГҮЙЛГЭЭНИЙ УДИРДЛАГА
# ========================================

@login_required
def bank_transaction_list(request):
    """Банкны гүйлгээний жагсаалт - эсрэг данс холбох, журналд оруулах"""
    from django.core.paginator import Paginator
    
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан бодогч, менежер роль эсвэл банкны гүйлгээ харах эрхтэй
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        profile.role == 'MANAGER' or
        user.is_superuser or
        user.has_perm('main.view_banktransaction')
    )
    
    if not has_access:
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    from django.db.models import Q

    # Зөвхөн банкны гүйлгээ (кассын гүйлгээ биш)
    transactions = BankTransaction.objects.filter(
        account_type='BANK'
    ).select_related(
        'bank_account', 'offset_account', 'income_sale__customer',
        'accounting_entry__debit_account', 'accounting_entry__credit_account'
    ).prefetch_related(
        'allocations__student', 'allocations__course',
        'sale_allocations__sale__customer'
    ).order_by('-transaction_date', '-id')
    
    # Банкны дансаар шүүх
    bank_account_id = request.GET.get('bank_account')
    if bank_account_id:
        transactions = transactions.filter(bank_account_id=bank_account_id)
    
    # Эсрэг дансаар шүүх
    offset_account_id = request.GET.get('offset_account')
    if offset_account_id:
        transactions = transactions.filter(offset_account_id=offset_account_id)
    
    # Тайлбараар хайх (SQLite-д Cyrillic case-insensitive ажиллахгүй)
    search_description = request.GET.get('description')
    if search_description:
        search_upper = search_description.upper()
        search_lower = search_description.lower()
        transactions = transactions.filter(
            Q(description__contains=search_description) |
            Q(description__contains=search_upper) |
            Q(description__contains=search_lower)
        )
    
    # Боловсруулалтын статусаар шүүх
    is_processed = request.GET.get('is_processed')
    if is_processed == 'false':
        transactions = transactions.filter(is_processed=False)
    elif is_processed == 'true':
        transactions = transactions.filter(is_processed=True)
    
    # Огноогоор шүүх
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        transactions = transactions.filter(transaction_date__gte=date_from)
    if date_to:
        transactions = transactions.filter(transaction_date__lte=date_to)

    # Орлого/Зарлагаар шүүх
    transaction_type = request.GET.get('transaction_type')
    if transaction_type == 'income':
        transactions = transactions.filter(income_amount__gt=0)
    elif transaction_type == 'expense':
        transactions = transactions.filter(expense_amount__gt=0)

    # Орлогын төрлөөр шүүх
    income_type = request.GET.get('income_type')
    if income_type:
        transactions = transactions.filter(income_type=income_type)

    # Зарлагын төрлөөр шүүх
    expense_type = request.GET.get('expense_type')
    if expense_type:
        transactions = transactions.filter(expense_type=expense_type)

    # Банкны нэрээр шүүх
    bank_name = request.GET.get('bank_name')
    if bank_name:
        transactions = transactions.filter(bank_name=bank_name)

    # Дүнгийн хязгаараар шүүх (гүйлгээ бүр зөвхөн орлого эсвэл зарлагатай тул
    # тэг биш талыг нь харгалзан шүүнэ)
    amount_min = request.GET.get('amount_min')
    amount_max = request.GET.get('amount_max')
    if amount_min:
        try:
            amount_min_val = Decimal(amount_min)
            transactions = transactions.filter(
                Q(income_amount__gte=amount_min_val) | Q(expense_amount__gte=amount_min_val)
            )
        except (InvalidOperation, ValueError, TypeError):
            pass
    if amount_max:
        try:
            amount_max_val = Decimal(amount_max)
            transactions = transactions.filter(
                Q(income_amount__gt=0, income_amount__lte=amount_max_val) |
                Q(expense_amount__gt=0, expense_amount__lte=amount_max_val)
            )
        except (InvalidOperation, ValueError, TypeError):
            pass

    # Сараар шүүх (сурагчийн төлбөрийн сар)
    # Тайлбар: USE_THOUSAND_SEPARATOR тохиргоо идэвхтэй тул template дээр {{ он }}
    # мэт бүхэл тоог таслалтай ("2,026") гаргаж болох тул цэвэрлэж авна.
    filter_month = request.GET.get('filter_month')
    filter_year = request.GET.get('filter_year')
    if filter_month:
        filter_month = filter_month.replace(',', '').strip()
    if filter_year:
        filter_year = filter_year.replace(',', '').strip()
    if filter_month:
        try:
            transactions = transactions.filter(income_month=int(filter_month))
        except (ValueError, TypeError):
            pass
    if filter_year:
        try:
            transactions = transactions.filter(income_year=int(filter_year))
        except (ValueError, TypeError):
            pass

    # Статистик тооцоолох
    total_count = transactions.count()
    unprocessed_count = transactions.filter(is_processed=False).count()
    processed_count = transactions.filter(is_processed=True).count()

    # Шүүлтэд тохирсон бүх гүйлгээний нийт дүн (хөл мөрөнд харуулах)
    amount_totals = transactions.aggregate(
        total_income=Sum('income_amount'),
        total_expense=Sum('expense_amount'),
    )
    total_income = amount_totals['total_income'] or Decimal('0')
    total_expense = amount_totals['total_expense'] or Decimal('0')

    # Pagination
    paginator = Paginator(transactions, 50)  # 50 гүйлгээ нэг хуудсанд
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Банкны дансууд (dropdown-д харуулах)
    bank_accounts = ChartOfAccounts.objects.filter(
        code__startswith='110',
        is_active=True
    ).order_by('code')
    
    # Бүх дансууд (эсрэг данс шүүлтэд)
    all_accounts = ChartOfAccounts.objects.filter(is_active=True).order_by('code')

    # Жилүүдийн жагсаалт (filter dropdown-д)
    from datetime import date as date_obj
    current_year = date_obj.today().year
    year_choices = list(range(current_year - 3, current_year + 2))

    context = {
        'transactions': page_obj,
        'bank_accounts': bank_accounts,
        'all_accounts': all_accounts,
        'total_count': total_count,
        'unprocessed_count': unprocessed_count,
        'processed_count': processed_count,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_total': total_income - total_expense,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        # Dropdown сонголтууд
        'income_type_choices': BankTransaction.INCOME_TYPE_CHOICES,
        'expense_type_choices': BankTransaction.EXPENSE_TYPE_CHOICES,
        'bank_choices': BankTransaction.BANK_CHOICES,
        'year_choices': year_choices,
        # Филтерийн утгууд (form-д харуулах)
        'selected_bank_account': bank_account_id,
        'selected_offset_account': offset_account_id,
        'search_description': search_description,
        'selected_is_processed': is_processed,
        'date_from': date_from,
        'date_to': date_to,
        'selected_transaction_type': transaction_type,
        'selected_income_type': income_type,
        'selected_expense_type': expense_type,
        'selected_bank_name': bank_name,
        'amount_min': amount_min,
        'amount_max': amount_max,
        'filter_month': filter_month,
        'filter_year': filter_year,
    }
    
    return render(request, 'main/bank_transaction_list.html', context)


@login_required
def link_bank_transaction_to_journal(request, transaction_id):
    """Банк/кассын гүйлгээнд эсрэг данс холбох, орлого ангилах, журналын бичилт үүсгэх"""
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан бодогч, Менежер бүлэг эсвэл банкны гүйлгээ засах эрхтэй
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.change_banktransaction')
    )
    
    if not has_access:
        messages.error(request, 'Энэ үйлдэл хийх эрх танд байхгүй.')
        return redirect('main:bank_transaction_list')
    
    # Гүйлгээ авах (банк болон кассын гүйлгээ хоёуланд зориулна)
    transaction = get_object_or_404(BankTransaction, id=transaction_id)

    # Автоматаар үүссэн кассын эсрэг мөр — холболтыг эх гүйлгээ хариуцна
    if transaction.transfer_source_id:
        messages.info(
            request,
            'Энэ кассын гүйлгээ харилцахын гүйлгээний холболтоос автоматаар үүссэн. '
            'Холболтыг эх гүйлгээн дээр удирдана.'
        )
        return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction.transfer_source_id)

    # GET болон POST хоёроос return_to уншина (форм POST хийхэд GET param алдагдаж болно)
    return_to = (request.POST.get('return_to') or request.GET.get('return_to', '')).strip()
    if return_to and (not return_to.startswith('/') or return_to.startswith('//')):
        return_to = ''

    def recalc_sale_paid_amount(sale_obj):
        """Борлуулалтын paid_amount-г legacy + partial allocation-аар дахин тооцоолно"""
        paid_legacy = BankTransaction.objects.filter(
            income_sale=sale_obj
        ).exclude(
            sale_allocations__isnull=False
        ).aggregate(s=Sum('income_amount'))['s'] or Decimal('0')

        paid_alloc = SalePaymentAllocation.objects.filter(
            sale=sale_obj
        ).aggregate(s=Sum('amount'))['s'] or Decimal('0')

        paid_total = paid_legacy + paid_alloc
        sale_obj.paid_amount = paid_total

        if paid_total >= sale_obj.total_amount and sale_obj.status == 'DRAFT':
            sale_obj.status = 'PAID'
        elif paid_total < sale_obj.total_amount and sale_obj.status == 'PAID':
            sale_obj.status = 'DRAFT'

        sale_obj.save(update_fields=['paid_amount', 'status'])
    
    if request.method == 'POST':
        # First handle unlink actions triggered from the link page (journal, split, allocation, sale link)
        unlink_type = request.POST.get('unlink_type', '').strip()
        if unlink_type:
            # return_to POST-оор ч ирж болно (form hidden input)
            _post_return = request.POST.get('return_to', '').strip()
            _effective_return = _post_return if (_post_return and _post_return.startswith('/') and not _post_return.startswith('//')) else return_to
            _link_url = reverse('main:link_bank_transaction_to_journal', args=[transaction_id])
            _back_url = _effective_return if _effective_return else _link_url
            try:
                # Unlink entire accounting entry attached to this transaction
                if unlink_type == 'journal':
                    if transaction.accounting_entry:
                        ae = transaction.accounting_entry
                        transaction.accounting_entry = None
                        transaction.is_processed = False
                        transaction.save(update_fields=['accounting_entry', 'is_processed'])
                        ae.delete()
                        from .import_bank_transactions import delete_cash_transfer_mirrors
                        delete_cash_transfer_mirrors(transaction)
                        messages.success(request, 'Гүйлгээн дэх журналын бичилт амжилттай цуцлагдлаа.')
                    else:
                        messages.error(request, 'Энэ гүйлгээнд холбогдсон журналын бичилт олдсонгүй.')
                    return redirect(_back_url)

                # Unlink a specific manual split's accounting entry (and optionally the split record)
                if unlink_type == 'split':
                    split_id = request.POST.get('split_id')
                    try:
                        from .models import BankTransactionSplit
                    except Exception:
                        BankTransactionSplit = None

                    if not BankTransactionSplit:
                        messages.error(request, 'Нэмэлт хуваарилалтын модель боломжитгүй байна (migration байхгүй).')
                        return redirect(_back_url)

                    bts = BankTransactionSplit.objects.filter(id=split_id, transaction=transaction).first()
                    if not bts:
                        messages.error(request, 'Сонгосон нэмэлт хуваарилалт олдсонгүй.')
                        return redirect(_back_url)
                    if bts.accounting_entry:
                        ae = bts.accounting_entry
                        bts.accounting_entry = None
                        bts.save(update_fields=['accounting_entry'])
                        ae.delete()
                        messages.success(request, 'Нэмэлт хуваарилалтын журналын бичилт цуцлагдлаа.')
                    else:
                        messages.error(request, 'Энэ мөрөнд холбогдсон журналын бичилт илрээгүй.')
                    return redirect(_back_url)

                # Unlink a specific payment allocation (student allocation)
                if unlink_type == 'alloc':
                    alloc_id = request.POST.get('alloc_id')
                    pa = PaymentAllocation.objects.filter(id=alloc_id, transaction=transaction).first()
                    if not pa:
                        messages.error(request, 'Сонгосон хуваарилалт олдсонгүй.')
                        return redirect(_back_url)
                    pa.delete()
                    messages.success(request, 'Хуваарилалт амжилттай устгагдлаа.')
                    return redirect(_back_url)

                # Unlink everything: journal, splits, allocations, sale link
                if unlink_type == 'all':
                    # remove sale allocations and payment allocations
                    SalePaymentAllocation.objects.filter(transaction=transaction).delete()
                    PaymentAllocation.objects.filter(transaction=transaction).delete()
                    # remove legacy income_sale link
                    if transaction.income_sale_id:
                        transaction.income_sale = None
                    # detach and delete accounting entry if present
                    if transaction.accounting_entry:
                        ae = transaction.accounting_entry
                        transaction.accounting_entry = None
                        ae.delete()
                    # автоматаар үүссэн кассын эсрэг мөрүүдийг устгах
                    from .import_bank_transactions import delete_cash_transfer_mirrors
                    delete_cash_transfer_mirrors(transaction)
                    transaction.offset_account = None
                    transaction.income_type = None
                    transaction.is_processed = False
                    transaction.save(update_fields=['income_sale', 'accounting_entry', 'is_processed', 'offset_account', 'income_type'])
                    messages.success(request, 'Гүйлгээний бүх холболт амжилттай цуцлагдлаа.')
                    return redirect(_back_url)

                if unlink_type in ('sale_alloc', 'sale'):
                    # remove SalePaymentAllocation for this transaction
                    SalePaymentAllocation.objects.filter(transaction=transaction).delete()
                    if transaction.income_sale_id:
                        transaction.income_sale = None
                    transaction.is_processed = False
                    transaction.save(update_fields=['income_sale', 'is_processed'])
                    messages.success(request, 'Борлуулалттай холболт амжилттай цуцлагдлаа.')
                    return redirect(_back_url)

                # Unlink a bank-to-bank transfer link
                if unlink_type == 'transfer':
                    from .import_bank_transactions import unlink_bank_transfer
                    if unlink_bank_transfer(transaction):
                        messages.success(request, 'Харилцах хоорондын шилжүүлгийн холболт цуцлагдлаа.')
                    else:
                        messages.error(request, 'Энэ гүйлгээнд холбогдсон шилжүүлэг олдсонгүй.')
                    return redirect(_back_url)
            except Exception as e:
                messages.error(request, f'Цуцлах явцад алдаа гарлаа: {e}')
                return redirect(_back_url)

        # Хоёр харилцахын гүйлгээг дотоод шилжүүлэг болгон холбох (тусдаа мини-форм)
        transfer_target_id = request.POST.get('link_transfer_target', '').replace(',', '').strip()
        if transfer_target_id:
            _post_return = request.POST.get('return_to', '').strip()
            _effective_return = _post_return if (_post_return and _post_return.startswith('/') and not _post_return.startswith('//')) else return_to
            _link_url = reverse('main:link_bank_transaction_to_journal', args=[transaction_id])
            _back_url = _effective_return if _effective_return else _link_url

            target = BankTransaction.objects.select_related('bank_account').filter(id=transfer_target_id).first()
            if not target:
                messages.error(request, 'Сонгосон гүйлгээ олдсонгүй.')
                return redirect(_back_url)

            if transaction.account_type != 'BANK' or target.account_type != 'BANK':
                messages.error(request, 'Зөвхөн харилцахын (банкны) гүйлгээг холбож болно.')
                return redirect(_back_url)
            if transaction.bank_account_id == target.bank_account_id:
                messages.error(request, 'Ижил дансны гүйлгээг хооронд нь холбож болохгүй.')
                return redirect(_back_url)
            if transaction.accounting_entry_id or target.accounting_entry_id:
                messages.error(request, 'Аль нэг гүйлгээ аль хэдийн журналд холбогдсон байна. Эхлээд холболтыг тасална уу.')
                return redirect(_back_url)

            if transaction.expense_amount > 0 and target.income_amount > 0:
                expense_tx, income_tx = transaction, target
            elif transaction.income_amount > 0 and target.expense_amount > 0:
                expense_tx, income_tx = target, transaction
            else:
                messages.error(request, 'Нэг тал зарлага, нөгөө тал орлоготой гүйлгээ байх ёстой.')
                return redirect(_back_url)

            if expense_tx.expense_amount != income_tx.income_amount:
                messages.error(
                    request,
                    f'Дүн таарахгүй байна: зарлага {expense_tx.expense_amount:,.0f}₮, орлого {income_tx.income_amount:,.0f}₮.'
                )
                return redirect(_back_url)

            try:
                from .import_bank_transactions import link_bank_transfer
                link_bank_transfer(expense_tx, income_tx, request.user)
                messages.success(request, 'Хоёр харилцахын гүйлгээ дотоод шилжүүлэг болгон амжилттай холбогдлоо.')
            except Exception as e:
                messages.error(request, f'Холбох явцад алдаа гарлаа: {e}')
            return redirect(_back_url)

        offset_account_id = request.POST.get('offset_account')

        if not offset_account_id:
            messages.error(request, 'Эсрэг данс сонгоно уу.')
            return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)

        try:
            offset_account = ChartOfAccounts.objects.get(id=offset_account_id)
            
            # Эсрэг данс хадгалах
            transaction.offset_account = offset_account
            
            # Мөнгөн гүйлгээний үзүүлэлт хадгалах
            cash_flow_indicator_id = request.POST.get('cash_flow_indicator')
            if cash_flow_indicator_id:
                transaction.cash_flow_indicator_id = cash_flow_indicator_id
            
            # Орлогын ангилал хадгалах (орлого бол)
            if transaction.income_amount > 0:
                income_type = request.POST.get('income_type', '').strip()
                new_income_type = request.POST.get('new_income_type', '').strip()
                if new_income_type:
                    income_type = new_income_type[:50]
                if income_type:
                    transaction.income_type = income_type
                    
                    # Сурагчийн төлбөр бол - олон хуваарилалт хадгална
                    if income_type == 'STUDENT_PAYMENT':
                        old_sale_ids = set(transaction.sale_allocations.values_list('sale_id', flat=True))
                        if transaction.income_sale_id:
                            old_sale_ids.add(transaction.income_sale_id)

                        mixed_sale_enabled = request.POST.get('mixed_sale_enabled') == '1'
                        mixed_sale_id = request.POST.get('mixed_sale_id', '').strip()
                        mixed_sale_amount_raw = request.POST.get('mixed_sale_amount', '').replace(',', '').strip()
                        mixed_sale_amount = Decimal('0')

                        if mixed_sale_enabled:
                            if not mixed_sale_id:
                                messages.error(request, 'Барааны төлбөрийн борлуулалт сонгоно уу.')
                                return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)
                            try:
                                mixed_sale_amount = Decimal(mixed_sale_amount_raw or '0')
                            except Exception:
                                messages.error(request, 'Барааны төлбөрийн дүн буруу байна.')
                                return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)

                            if mixed_sale_amount <= 0:
                                messages.error(request, 'Барааны төлбөрийн дүн 0-ээс их байх ёстой.')
                                return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)
                            if mixed_sale_amount > transaction.income_amount:
                                messages.error(request, 'Барааны төлбөрийн дүн гүйлгээний дүнгээс их байж болохгүй.')
                                return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)

                            mixed_sale_obj = Sale.objects.filter(id=mixed_sale_id).first()
                            if not mixed_sale_obj:
                                messages.error(request, 'Сонгосон борлуулалт олдсонгүй.')
                                return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)

                            paid_legacy_other = BankTransaction.objects.filter(
                                income_sale=mixed_sale_obj
                            ).exclude(
                                sale_allocations__isnull=False
                            ).exclude(
                                id=transaction.id
                            ).aggregate(s=Sum('income_amount'))['s'] or Decimal('0')

                            paid_alloc_other = SalePaymentAllocation.objects.filter(
                                sale=mixed_sale_obj
                            ).exclude(
                                transaction=transaction
                            ).aggregate(s=Sum('amount'))['s'] or Decimal('0')

                            remaining_for_sale = mixed_sale_obj.total_amount - (paid_legacy_other + paid_alloc_other)
                            if remaining_for_sale <= 0:
                                messages.error(request, 'Сонгосон борлуулалтын төлбөр бүрэн холбогдсон байна.')
                                return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)

                            if mixed_sale_amount > remaining_for_sale:
                                messages.error(
                                    request,
                                    f'Сонгосон борлуулалтад нэмээд {remaining_for_sale:,.0f}₮ хүртэл холбож болно.'
                                )
                                return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)

                        target_student_amount = transaction.income_amount - mixed_sale_amount

                        # Эхлээд POST-оос ирсэн хуваарилалтуудыг зөвхөн задлан уншиж,
                        # дүнг шалгана — өгөгдлийн санд ЮУ Ч бичихгүй. Хэрэв дүн
                        # гүйлгээний дүнгээс их бол алдаа гарган, хуучин
                        # хуваарилалтад хүрэлгүй, шинийг ч үүсгэхгүйгээр зогсоно.
                        parsed_allocations = []
                        total_allocated = Decimal(0)
                        allocation_parse_error = False

                        for key, value in request.POST.items():
                            if key.startswith('allocations[') and '[student]' in key:
                                # allocations[1][student] -> 1 гэж parse хийх
                                allocation_id = key.split('[')[1].split(']')[0]

                                student_id = request.POST.get(f'allocations[{allocation_id}][student]')
                                course_id = request.POST.get(f'allocations[{allocation_id}][course]')
                                month_year = request.POST.get(f'allocations[{allocation_id}][month_year]')
                                amount = request.POST.get(f'allocations[{allocation_id}][amount]')

                                if student_id and course_id and month_year and amount:
                                    try:
                                        # Он/сар задлах (2026-02 -> year=2026, month=2)
                                        year_str, month_str = month_year.split('-')
                                        alloc_amount = Decimal(amount)
                                        parsed_allocations.append({
                                            'student_id': student_id,
                                            'course_id': course_id,
                                            'month': int(month_str),
                                            'year': int(year_str),
                                            'amount': alloc_amount,
                                        })
                                        total_allocated += alloc_amount
                                    except Exception as e:
                                        print(f"Allocation parse error: {e}")
                                        allocation_parse_error = True

                        if allocation_parse_error:
                            messages.error(request, 'Хуваарилалтын мэдээлэл буруу байна. Дахин шалгаад оруулна уу.')
                            return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)

                        if total_allocated > target_student_amount:
                            messages.error(
                                request,
                                f'Сургалтын хуваарилалтын дүн ({total_allocated:,.0f}₮) '
                                f'зөвшөөрөгдөх дүнгээс ({target_student_amount:,.0f}₮) их байна.'
                            )
                            return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)

                        allocations_saved = len(parsed_allocations)

                        if allocations_saved == 0:
                            if target_student_amount > 0:
                                messages.error(
                                    request,
                                    f'Сургалтын төлбөрийн {target_student_amount:,.0f}₮ дүнг хуваарилалтаар бүрэн холбоно уу.'
                                )
                                return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)
                        else:
                            # Нийт дүн шалгах
                            if total_allocated != target_student_amount:
                                messages.error(
                                    request,
                                    f'Хуваарилалтын нийт дүн ({total_allocated:,.0f}₮) '
                                    f'сургалтын төлбөрийн дүнтэй ({target_student_amount:,.0f}₮) тэнцүү байх ёстой.'
                                )
                                return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)

                        # Бүх шалгалтыг давсны дараа л хуучныг устгаж, шинийг үүсгэнэ
                        PaymentAllocation.objects.filter(transaction=transaction).delete()
                        transaction.sale_allocations.all().delete()

                        for alloc_data in parsed_allocations:
                            PaymentAllocation.objects.create(transaction=transaction, **alloc_data)

                        # Хуучин fields-үүдийг цэвэрлэх
                        transaction.income_student = None
                        transaction.income_course = None
                        transaction.income_month = None
                        transaction.income_year = None
                        transaction.income_sale = None

                        affected_sale_ids = set(old_sale_ids)
                        if mixed_sale_enabled and mixed_sale_id and mixed_sale_amount > 0:
                            SalePaymentAllocation.objects.update_or_create(
                                transaction=transaction,
                                sale_id=int(mixed_sale_id),
                                defaults={'amount': mixed_sale_amount}
                            )
                            affected_sale_ids.add(int(mixed_sale_id))

                        for sale_id in affected_sale_ids:
                            sale_obj = Sale.objects.filter(id=sale_id).first()
                            if sale_obj:
                                recalc_sale_paid_amount(sale_obj)
                    
                    # Барааны борлуулалт бол
                    elif income_type == 'PRODUCT_SALE':
                        sale_id = request.POST.get('sale')
                        if not sale_id:
                            messages.error(request, 'Барааны борлуулалтын төрөл сонгосон тул борлуулалтын баримт заавал сонгоно уу.')
                            return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)

                        sale_obj = Sale.objects.filter(id=sale_id).first()
                        if not sale_obj:
                            messages.error(request, 'Сонгосон борлуулалт олдсонгүй.')
                            return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)

                        paid_legacy_other = BankTransaction.objects.filter(
                            income_sale=sale_obj
                        ).exclude(
                            sale_allocations__isnull=False
                        ).exclude(
                            id=transaction.id
                        ).aggregate(s=Sum('income_amount'))['s'] or Decimal('0')

                        paid_alloc_other = SalePaymentAllocation.objects.filter(
                            sale=sale_obj
                        ).exclude(
                            transaction=transaction
                        ).aggregate(s=Sum('amount'))['s'] or Decimal('0')

                        remaining_for_sale = sale_obj.total_amount - (paid_legacy_other + paid_alloc_other)
                        if remaining_for_sale <= 0:
                            messages.error(request, 'Сонгосон борлуулалтын төлбөр бүрэн холбогдсон байна.')
                            return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)

                        if transaction.income_amount > remaining_for_sale:
                            messages.error(
                                request,
                                f'Энэ гүйлгээнээс сонгосон борлуулалтад {remaining_for_sale:,.0f}₮-с их холбож болохгүй.'
                            )
                            return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)

                        transaction.income_sale_id = sale_id
                        transaction.income_student = None
                        transaction.income_course = None
                        transaction.income_month = None

                        # Борлуулалтад урьдчилан зааж өгсөн нэмэлт хуваарилалтуудыг
                        # BankTransactionSplit-д автоматаар шилжүүлэх
                        # (модель устгагдсан байж болно — тиймээс хамгаалалттай)
                        try:
                            from .models import BankTransactionSplit, SaleExtraSplit
                        except Exception:
                            BankTransactionSplit = None
                            SaleExtraSplit = None
                        if BankTransactionSplit and SaleExtraSplit:
                            sale_extra_splits = sale_obj.extra_splits.all()
                            if sale_extra_splits.exists():
                                transaction.extra_splits.all().delete()
                                for ses in sale_extra_splits:
                                    BankTransactionSplit.objects.get_or_create(
                                        transaction=transaction,
                                        account=ses.account,
                                        defaults={'amount': ses.amount, 'description': ses.description or ''}
                                    )
                    
                    # Бусад төрөл
                    else:
                        transaction.income_student = None
                        transaction.income_course = None
                        transaction.income_month = None
                        transaction.income_sale = None
            
            transaction.save()
            
            # Нэмэлт хуваарилалт (extra splits) хадгалах
            try:
                from .models import BankTransactionSplit
            except Exception:
                BankTransactionSplit = None
            if BankTransactionSplit:
                transaction.extra_splits.all().delete()
            total_split = Decimal('0')
            split_errors = []
            split_index = 0
            while BankTransactionSplit:
                acct_id = request.POST.get(f'splits[{split_index}][account]', '').strip()
                amt_raw = request.POST.get(f'splits[{split_index}][amount]', '').replace(',', '').strip()
                desc = request.POST.get(f'splits[{split_index}][description]', '').strip()
                if not acct_id and not amt_raw:
                    break
                split_index += 1
                if not acct_id or not amt_raw:
                    split_errors.append(f'Мөр {split_index}: данс болон дүн заавал')
                    continue
                try:
                    split_amt = Decimal(amt_raw)
                    if split_amt <= 0:
                        split_errors.append(f'Мөр {split_index}: дүн 0-ээс их байх ёстой')
                        continue
                    split_acct = ChartOfAccounts.objects.get(id=acct_id)
                    BankTransactionSplit.objects.create(
                        transaction=transaction,
                        account=split_acct,
                        amount=split_amt,
                        description=desc,
                    )
                    total_split += split_amt
                except ChartOfAccounts.DoesNotExist:
                    split_errors.append(f'Мөр {split_index}: данс олдсонгүй')
                except Exception as e:
                    split_errors.append(f'Мөр {split_index}: {e}')

            if split_errors:
                messages.error(request, 'Нэмэлт хуваарилалтын алдаа: ' + '; '.join(split_errors))
                return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)

            total_amount = transaction.income_amount if transaction.income_amount > 0 else transaction.expense_amount
            if total_split >= total_amount:
                messages.error(
                    request,
                    f'Нэмэлт хуваарилалтын нийт дүн ({total_split:,.0f}₮) гүйлгээний нийт дүн ({total_amount:,.0f}₮)-с их буюу тэнцүү байж болохгүй.'
                )
                return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)

            # Журналын бичилт үүсгэх
            from .import_bank_transactions import (
                regenerate_accounting_entries, create_accounting_entry_safe, next_entry_number
            )

            # Борлуулалттай холбогдсон бол (offset_account байхгүй ч) splits-д журнал үүсгэнэ
            sale_linked = (transaction.income_sale_id or
                          transaction.sale_allocations.exists())
            if sale_linked:
                # Банкны данс тодорхойлох
                bt_bank_acct = transaction.bank_account
                date_key = transaction.transaction_date.strftime('%Y%m%d')
                prefix = 'CSH' if transaction.account_type == 'CASH' else 'BNK'

                # Борлуулалтын SaleExtraSplit → BankTransactionSplit + AccountingEntry шилжүүлэх
                linked_sale = transaction.income_sale
                if linked_sale and bt_bank_acct:
                    try:
                        from .models import BankTransactionSplit
                    except Exception:
                        BankTransactionSplit = None
                    if BankTransactionSplit:
                        for ses in linked_sale.extra_splits.all():
                            bts, created = BankTransactionSplit.objects.get_or_create(
                                transaction=transaction,
                                account=ses.account,
                                defaults={'amount': ses.amount, 'description': ses.description or ''}
                            )
                            if not bts.accounting_entry:
                                _, split_entry_number = next_entry_number(f'{prefix}{date_key}')
                                split_desc = ses.description or transaction.description
                                split_entry = create_accounting_entry_safe(
                                    entry_date=transaction.transaction_date,
                                    entry_number=split_entry_number,
                                    description=split_desc,
                                    debit_account=bt_bank_acct,
                                    debit_amount=bts.amount,
                                    credit_account=ses.account,
                                    credit_amount=bts.amount,
                                    created_by=request.user,
                                )
                                bts.accounting_entry = split_entry
                                bts.save(update_fields=['accounting_entry'])

                    # If there's no offset_account but the transaction links a Sale,
                    # create a main journal entry debiting the bank and crediting
                    # the standard revenue account so the sale appears in journal.
                    if not transaction.offset_account and not transaction.accounting_entry:
                        try:
                            # total of extra_splits on transaction (if model exists)
                            if hasattr(transaction, 'extra_splits'):
                                try:
                                    main_splits_total = sum(s.amount for s in transaction.extra_splits.all())
                                except Exception:
                                    main_splits_total = Decimal('0')
                            else:
                                main_splits_total = Decimal('0')

                            main_amount = (transaction.income_amount or Decimal('0')) - main_splits_total
                            if main_amount > 0:
                                revenue_account = ChartOfAccounts.objects.filter(code='510101').first()
                                if revenue_account:
                                    _, main_entry_number = next_entry_number(f'{prefix}{date_key}')
                                    main_entry = create_accounting_entry_safe(
                                        entry_date=transaction.transaction_date,
                                        entry_number=main_entry_number,
                                        description=transaction.description,
                                        debit_account=bt_bank_acct,
                                        debit_amount=main_amount,
                                        credit_account=revenue_account,
                                        credit_amount=main_amount,
                                        created_by=request.user,
                                    )
                                    transaction.accounting_entry = main_entry
                                    transaction.is_processed = True
                                    transaction.save(update_fields=['accounting_entry', 'is_processed'])
                        except Exception:
                            # Don't block the overall flow on this best-effort create
                            pass

                # Үндсэн борлуулалтын орлогын журнал (offset_account байгаа бол)
                if transaction.offset_account and not transaction.accounting_entry:
                    if hasattr(transaction, 'extra_splits'):
                        try:
                            main_splits_total = sum(s.amount for s in transaction.extra_splits.all())
                        except Exception:
                            main_splits_total = Decimal('0')
                    else:
                        main_splits_total = Decimal('0')
                    main_amount = transaction.income_amount - main_splits_total
                    if main_amount > 0 and bt_bank_acct:
                        _, main_entry_number = next_entry_number(f'{prefix}{date_key}')
                        main_entry = create_accounting_entry_safe(
                            entry_date=transaction.transaction_date,
                            entry_number=main_entry_number,
                            description=transaction.description,
                            debit_account=bt_bank_acct,
                            debit_amount=main_amount,
                            credit_account=transaction.offset_account,
                            credit_amount=main_amount,
                            created_by=request.user,
                        )
                        transaction.accounting_entry = main_entry
                        transaction.is_processed = True
                        transaction.save(update_fields=['accounting_entry', 'is_processed'])

                # Мануал splits (form-оос оруулсан) бүрт журнал үүсгэнэ
                if bt_bank_acct:
                    if hasattr(transaction, 'extra_splits'):
                        for split in transaction.extra_splits.filter(accounting_entry__isnull=True):
                            _, split_entry_number = next_entry_number(f'{prefix}{date_key}')
                            split_desc = split.description or transaction.description
                            split_entry = create_accounting_entry_safe(
                                entry_date=transaction.transaction_date,
                                entry_number=split_entry_number,
                                description=split_desc,
                                debit_account=bt_bank_acct,
                                debit_amount=split.amount,
                                credit_account=split.account,
                                credit_amount=split.amount,
                                created_by=request.user,
                            )
                            split.accounting_entry = split_entry
                            split.save(update_fields=['accounting_entry'])

                # Эсрэг данс касс бол кассын эсрэг мөрийг синк хийх
                from .import_bank_transactions import sync_cash_transfer_mirrors
                sync_cash_transfer_mirrors(transaction, request.user)

                messages.success(
                    request,
                    f'✓ Борлуулалт холбогдож, журналын бичилт үүслээ!'
                )
                if return_to and return_to.startswith('/') and not return_to.startswith('//'):
                    return redirect(return_to)
                if transaction.account_type == 'CASH':
                    return redirect('main:cash_transaction_list')
                else:
                    return redirect('main:bank_transaction_list')

            # Энэ нэг гүйлгээний журнал үүсгэх (offset_account аргаар)
            result = regenerate_accounting_entries([transaction], request.user)

            if result > 0:
                messages.success(
                    request, 
                    f'✓ Эсрэг данс "{offset_account.code} - {offset_account.name}" холбогдож, '
                    f'журналын бичилт үүслээ!'
                )
                # Банк эсвэл кассын жагсаалт руу буцах
                if return_to and return_to.startswith('/') and not return_to.startswith('//'):
                    return redirect(return_to)
                if transaction.account_type == 'CASH':
                    return redirect('main:cash_transaction_list')
                else:
                    return redirect('main:bank_transaction_list')
            else:
                messages.warning(
                    request,
                    'Эсрэг данс хадгалагдсан боловч журналын бичилт үүсгэх боломжгүй. '
                    'Admin хэсгээс "Журналын бичилт үүсгэх" үйлдлийг ашиглана уу.'
                )
                # Банк эсвэл кассын жагсаалт руу буцах
                if return_to and return_to.startswith('/') and not return_to.startswith('//'):
                    return redirect(return_to)
                if transaction.account_type == 'CASH':
                    return redirect('main:cash_transaction_list')
                else:
                    return redirect('main:bank_transaction_list')
                
        except ChartOfAccounts.DoesNotExist:
            messages.error(request, 'Сонгосон данс олдсонгүй.')
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
            return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)
    
    # GET хүсэлт - форм харуулах
    # Бүх идэвхтэй дансуудыг харуулах
    all_accounts = ChartOfAccounts.objects.filter(is_active=True).order_by('code')
    
    # Мөнгөн гүйлгээний үзүүлэлтүүд (орлого/зарлага-аар шүүнэ JavaScript дээр)
    cash_flow_indicators = CashFlowIndicator.objects.filter(is_active=True).order_by('code')
    
    # Орлого/зарлагаар ангилах (зөвлөмж болгоход)
    income_accounts = all_accounts.filter(code__startswith='4')
    expense_accounts = all_accounts.filter(code__startswith='5')
    asset_accounts = all_accounts.filter(code__startswith='1')
    liability_accounts = all_accounts.filter(code__startswith='2')
    equity_accounts = all_accounts.filter(code__startswith='3')
    
    # Орлогын ангилалд хэрэгтэй өгөгдөл
    students = UserProfile.objects.filter(role=UserRole.STUDENT).select_related('user').order_by('first_name', 'last_name')
    courses = Course.objects.filter(is_active=True).order_by('level', 'name')
    months = [(i, f'{i}-р сар') for i in range(1, 13)]

    # Одоо байгаа хуваарилалтууд
    existing_allocations = transaction.allocations.all().select_related('student', 'course')
    existing_sale_allocation = transaction.sale_allocations.select_related('sale').first()

    # Борлуулалтын жагсаалт: бүрэн холбогдсон борлуулалтыг dropdown-оос нуух
    # (гэхдээ энэ гүйлгээнд аль хэдийн сонгогдсон борлуулалтыг засварлахын тулд заавал үлдээнэ)
    selected_sale_ids = set()
    if transaction.income_sale_id:
        selected_sale_ids.add(transaction.income_sale_id)
    if existing_sale_allocation and existing_sale_allocation.sale_id:
        selected_sale_ids.add(existing_sale_allocation.sale_id)

    # Банкны гүйлгээнд холбогдсон борлуулалтын ID-ууд (одоогийн гүйлгээнийхийг оруулахгүй)
    linked_sale_ids = set(
        BankTransaction.objects.filter(income_sale__isnull=False)
        .exclude(id=transaction.id)
        .values_list('income_sale_id', flat=True)
    ) | set(
        SalePaymentAllocation.objects.exclude(transaction=transaction)
        .values_list('sale_id', flat=True)
    )

    # Бүх цуцлагдаагүй борлуулалтыг авах (Банкны холбоо шүүлтүүрт зориулж бүгдийг дамжуулна)
    sales = list(
        Sale.objects.exclude(status='CANCELLED')
        .filter(expected_payment_method__icontains='Харилцах')
        .select_related('customer')
        .order_by('-sale_date')
    )
    # Одоогийн гүйлгээнд сонгогдсон борлуулалтыг заавал оруулах (payment method харгалзахгүй)
    if selected_sale_ids:
        existing_selected = Sale.objects.filter(id__in=selected_sale_ids).select_related('customer')
        existing_ids_in_list = {s.id for s in sales}
        for s in existing_selected:
            if s.id not in existing_ids_in_list:
                sales.insert(0, s)
    # Борлуулалт бүрд is_linked тэмдэглэгэ нэмэх (JS шүүлтүүрт ашиглана)
    for sale in sales:
        sale.is_linked = sale.id in linked_sale_ids
    # remaining_for_link тооцоолол (харуулах зорилгоор)
    for sale in sales:
        sale.remaining_for_link = sale.total_amount - sale.paid_amount if hasattr(sale, 'paid_amount') else sale.total_amount
    
    # Жагсаалтаас орж ирэхэд орлогын төрлийг урьдчилан сонгож болно
    income_type_codes = {code for code, _ in BankTransaction.INCOME_TYPE_CHOICES}
    initial_income_type = request.GET.get('income_type', '').strip()
    if initial_income_type not in income_type_codes:
        initial_income_type = ''

    # Өмнө нь "Шинэ орлогын төрөл" талбараар нэмэгдсэн, стандарт жагсаалтад ороогүй
    # төрлүүдийг сонголтод харагдуулах (жишээ: Тэтгэлэг)
    custom_income_types = (
        BankTransaction.objects
        .exclude(income_type__isnull=True)
        .exclude(income_type='')
        .exclude(income_type__in=income_type_codes)
        .order_by('income_type')
        .values_list('income_type', flat=True)
        .distinct()
    )
    income_types = list(BankTransaction.INCOME_TYPE_CHOICES) + [(t, t) for t in custom_income_types]

    # Нэмэлт хуваарилалтууд (модель устгагдсан байж болно)
    if hasattr(transaction, 'extra_splits'):
        existing_splits = transaction.extra_splits.select_related('account').all()
    else:
        existing_splits = []

    # Харилцах хоорондын шилжүүлэг холбох — эсрэг талын нээлттэй (журналгүй) гүйлгээг хайх
    transfer_link = transaction.transfer_link
    transfer_candidates = []
    tf_desc = request.GET.get('tf_desc', '').strip()
    tf_date_from = request.GET.get('tf_date_from', '').strip()
    tf_date_to = request.GET.get('tf_date_to', '').strip()
    tf_search_active = bool(tf_desc or tf_date_from or tf_date_to)

    can_search_transfer = (
        transaction.account_type == 'BANK' and not transfer_link and
        not transaction.accounting_entry_id and
        (transaction.income_amount > 0 or transaction.expense_amount > 0)
    )
    if can_search_transfer:
        # Зөвхөн тухайн гүйлгээтэй яг ижил дүнтэй эсрэг талын гүйлгээг санал болгоно
        # (өөр дүнтэй бол ямар ч тохиолдолд холбогдож чадахгүй тул).
        if transaction.expense_amount > 0:
            candidates_qs = BankTransaction.objects.filter(account_type='BANK', income_amount=transaction.expense_amount)
        else:
            candidates_qs = BankTransaction.objects.filter(account_type='BANK', expense_amount=transaction.income_amount)

        candidates_qs = candidates_qs.exclude(
            bank_account_id=transaction.bank_account_id
        ).filter(
            accounting_entry__isnull=True
        ).select_related('bank_account')

        if tf_desc:
            candidates_qs = candidates_qs.filter(
                Q(description__icontains=tf_desc) | Q(counterparty_name__icontains=tf_desc)
            )
        if tf_date_from:
            candidates_qs = candidates_qs.filter(transaction_date__gte=tf_date_from)
        if tf_date_to:
            candidates_qs = candidates_qs.filter(transaction_date__lte=tf_date_to)

        if not tf_search_active:
            from datetime import timedelta
            candidates_qs = candidates_qs.filter(
                transaction_date__gte=transaction.transaction_date - timedelta(days=14),
                transaction_date__lte=transaction.transaction_date + timedelta(days=14),
            )

        transfer_candidates = list(candidates_qs.order_by('-transaction_date')[:30])

    context = {
        'transaction': transaction,
        'all_accounts': all_accounts,
        'income_accounts': income_accounts,
        'expense_accounts': expense_accounts,
        'asset_accounts': asset_accounts,
        'liability_accounts': liability_accounts,
        'equity_accounts': equity_accounts,
        'students': students,
        'courses': courses,
        'sales': sales,
        'months': months,
        'income_types': income_types,
        'cash_flow_indicators': cash_flow_indicators,
        'existing_allocations': existing_allocations,
        'existing_sale_allocation': existing_sale_allocation,
        'initial_income_type': initial_income_type,
        'existing_splits': existing_splits,
        'transfer_link': transfer_link,
        'transfer_candidates': transfer_candidates,
        'tf_desc': tf_desc,
        'tf_date_from': tf_date_from,
        'tf_date_to': tf_date_to,
        'return_to': request.GET.get('return_to', ''),
    }

    return render(request, 'main/link_bank_transaction.html', context)


@login_required
def classify_income(request, transaction_id):
    """Банкны гүйлгээний орлогыг ангилах - төрөл, сурагч, бараа (олон хуваарилалт дэмжинэ)"""
    from datetime import datetime
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан бодогч, Менежер бүлэг эсвэл орлого ангилах эрхтэй
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.change_banktransaction')
    )
    
    if not has_access:
        messages.error(request, 'Энэ үйлдэл хийх эрх танд байхгүй.')
        return redirect('main:bank_transaction_list')
    
    # Гүйлгээ авах
    transaction = get_object_or_404(BankTransaction, id=transaction_id)
    
    # Зөвхөн орлогын гүйлгээг ангилна
    if transaction.income_amount == 0:
        messages.error(request, 'Энэ гүйлгээ орлого биш тул ангилах боломжгүй.')
        return redirect('main:bank_transaction_list')
    
    if request.method == 'POST':
        income_type = request.POST.get('income_type')
        
        if not income_type:
            messages.error(request, 'Орлогын төрөл сонгоно уу.')
            return redirect('main:classify_income', transaction_id=transaction_id)
        
        try:
            # Төрөл хадгалах
            transaction.income_type = income_type
            
            # Сурагчийн төлбөр бол - олон хуваарилалт үүсгэх
            if income_type == 'STUDENT_PAYMENT':
                # Хуучин хуваарилалтуудыг устгах
                transaction.allocations.all().delete()
                
                # Шинэ хуваарилалтуудыг үүсгэх
                allocation_count = int(request.POST.get('allocation_count', 0))
                
                if allocation_count == 0:
                    messages.error(request, 'Хамгийн багадаа 1 хуваарилалт үүсгэх хэрэгтэй.')
                    return redirect('main:classify_income', transaction_id=transaction_id)
                
                total_allocated = Decimal(0)
                created_allocations = []
                
                for i in range(allocation_count):
                    student_id = request.POST.get(f'student_{i}')
                    course_id = request.POST.get(f'course_{i}')
                    month = request.POST.get(f'month_{i}')
                    year = request.POST.get(f'year_{i}')
                    amount = request.POST.get(f'amount_{i}')
                    comment = request.POST.get(f'comment_{i}', '')
                    
                    # Дутуу өгөгдөл шалгах
                    if not all([student_id, course_id, month, year, amount]):
                        messages.error(request, f'Хуваарилалт #{i+1}: Бүх талбарыг бөглөнө үү.')
                        return redirect('main:classify_income', transaction_id=transaction_id)
                    
                    try:
                        student = UserProfile.objects.get(id=student_id, role=UserRole.STUDENT)
                        course = Course.objects.get(id=course_id)
                        allocation_amount = Decimal(amount)
                        
                        # Хуваарилалт үүсгэх
                        allocation = PaymentAllocation.objects.create(
                            transaction=transaction,
                            student=student,
                            course=course,
                            month=int(month),
                            year=int(year),
                            amount=allocation_amount,
                            comment=comment
                        )
                        
                        total_allocated += allocation_amount
                        created_allocations.append(allocation)
                        
                    except (UserProfile.DoesNotExist, Course.DoesNotExist) as e:
                        messages.error(request, f'Хуваарилалт #{i+1}: Өгөгдөл олдсонгүй.')
                        return redirect('main:classify_income', transaction_id=transaction_id)
                
                # Нийт дүн шалгах
                if total_allocated != transaction.income_amount:
                    messages.warning(request, 
                        f'Анхааруулга: Хуваарилалтын нийт дүн ({total_allocated:,.0f}₮) гүйлгээний дүнтэй ({transaction.income_amount:,.0f}₮) таарахгүй байна.')
                
                # Хуучин income_student/month устгах (одоо allocations ашиглана)
                transaction.income_student = None
                transaction.income_month = None
                transaction.income_year = None
                transaction.income_course = None
                transaction.income_sale = None
            
            # Барааны борлуулалт бол
            elif income_type == 'PRODUCT_SALE':
                sale_id = request.POST.get('sale')
                
                if sale_id:
                    sale = Sale.objects.get(id=sale_id)
                    transaction.income_sale = sale
                transaction.income_student = None
                transaction.income_month = None
                transaction.income_year = None
                transaction.income_course = None
                
                # Хуваарилалт устгах
                transaction.allocations.all().delete()
            
            # Бусад төрөл
            else:
                transaction.income_student = None
                transaction.income_month = None
                transaction.income_year = None
                transaction.income_course = None
                transaction.income_sale = None
                
                # Хуваарилалт устгах
                transaction.allocations.all().delete()
            
            transaction.save()
            
            if income_type == 'STUDENT_PAYMENT':
                messages.success(request, f'✓ Орлогын ангилал хадгалагдлаа: {created_allocations.__len__()} хуваарилалт үүсгэгдлээ.')
            else:
                messages.success(request, f'✓ Орлогын ангилал хадгалагдлаа: {transaction.get_income_type_display()}')
            
            return redirect('main:bank_transaction_list')
            
        except Sale.DoesNotExist:
            messages.error(request, 'Борлуулалт олдсонгүй.')
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
            import traceback
            traceback.print_exc()
            return redirect('main:classify_income', transaction_id=transaction_id)
    
    # GET хүсэлт - форм харуулах
    students = UserProfile.objects.filter(role=UserRole.STUDENT).order_by('first_name', 'last_name')
    # Банкны гүйлгээнд холбогдсон борлуулалтын ID-ууд (одоогийн гүйлгээнийхийг оруулахгүй)
    _linked_via_fk = set(
        BankTransaction.objects.filter(income_sale__isnull=False)
        .exclude(id=transaction.id)
        .values_list('income_sale_id', flat=True)
    )
    _linked_via_alloc = set(
        SalePaymentAllocation.objects.exclude(transaction=transaction)
        .values_list('sale_id', flat=True)
    )
    already_linked_sale_ids = _linked_via_fk | _linked_via_alloc
    # Одоогийн гүйлгээнд сонгогдсон борлуулалт жагсаалтаас хасагдахгүй байхаар
    _current_sale_ids = set()
    if transaction.income_sale_id:
        _current_sale_ids.add(transaction.income_sale_id)
    sales = Sale.objects.exclude(
        status='CANCELLED'
    ).exclude(
        id__in=already_linked_sale_ids - _current_sale_ids
    ).select_related('customer').order_by('-sale_date')
    courses = Course.objects.filter(is_active=True).order_by('level', 'name')
    
    # Сарын сонголт
    months = [
        (1, '1-р сар'), (2, '2-р сар'), (3, '3-р сар'),
        (4, '4-р сар'), (5, '5-р сар'), (6, '6-р сар'),
        (7, '7-р сар'), (8, '8-р сар'), (9, '9-р сар'),
        (10, '10-р сар'), (11, '11-р сар'), (12, '12-р сар'),
    ]
    
    # Оны сонголт (2024-2030)
    current_year = datetime.now().year
    years = list(range(2024, current_year + 2))
    
    # Одоо байгаа хуваарилалтууд
    existing_allocations = transaction.allocations.all().select_related('student', 'course')
    
    context = {
        'transaction': transaction,
        'students': students,
        'courses': courses,
        'sales': sales,
        'months': months,
        'years': years,
        'current_year': current_year,
        'income_types': BankTransaction.INCOME_TYPE_CHOICES,
        'existing_allocations': existing_allocations,
    }
    
    return render(request, 'main/classify_income.html', context)


# Төлбөрийн хуудас - тусдаа файлаас импортлох
from .views_payments import student_payments, update_payment_comment


@login_required
def get_student_courses(request, student_id):
    """Сурагчийн бүртгэлтэй ангиудыг JSON-аар буцаах"""
    from django.http import JsonResponse
    
    try:
        student = get_object_or_404(UserProfile, id=student_id, role=UserRole.STUDENT)
        
        # Сурагчийн бүртгэлтэй ангиудыг авах (is_active=True, цуцлаагүй)
        enrollments = Enrollment.objects.filter(
            student=student,
            is_active=True
        ).exclude(
            status='CANCELLED'
        ).select_related('course')
        
        # Анги мэдээллийг JSON-руу хувиргах
        courses = [
            {
                'id': enrollment.course.id,
                'name': enrollment.course.name,
                'level': enrollment.course.get_level_display(),
                'status': enrollment.get_status_display(),
            }
            for enrollment in enrollments
        ]
        
        return JsonResponse({'courses': courses})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def cash_transaction_create(request):
    """Кассын гүйлгээ шинээр оруулах"""
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан бодогч, Менежер бүлэг эсвэл касс үүсгэх эрхтэй
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.add_banktransaction')
    )
    
    if not has_access:
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    if request.method == 'POST':
        try:
            # Мэдээлэл цуглуулах
            transaction_date_str = request.POST.get('transaction_date')
            cash_account_code = request.POST.get('cash_account')
            income_amount = request.POST.get('income_amount') or 0
            expense_amount = request.POST.get('expense_amount') or 0
            description = request.POST.get('description')
            offset_account_id = request.POST.get('offset_account')
            income_type = request.POST.get('income_type')
            expense_type = request.POST.get('expense_type')
            cash_flow_indicator_id = request.POST.get('cash_flow_indicator')
            
            # Утга шалгах
            if not transaction_date_str or not cash_account_code or not description:
                messages.error(request, 'Огноо, кассын данс, тайлбар заавал бөглөнө үү.')
                raise ValueError("Required fields missing")
            
            # Огноог date объект болгох
            from datetime import datetime
            transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()
            
            # Орлого эсвэл зарлага заавал байх
            income_dec = Decimal(income_amount) if income_amount else Decimal('0')
            expense_dec = Decimal(expense_amount) if expense_amount else Decimal('0')
            
            if income_dec == 0 and expense_dec == 0:
                messages.error(request, 'Орлого эсвэл зарлага заавал бөглөнө үү.')
                raise ValueError("Amount required")
            
            if income_dec > 0 and expense_dec > 0:
                messages.error(request, 'Орлого эсвэл зарлага аль нэгийг л бөглөнө үү (хоёуланг биш).')
                raise ValueError("Both amounts entered")
            
            # Касс дансыг олох
            cash_account = ChartOfAccounts.objects.get(code=cash_account_code)
            
            # Эсрэг данс (сонголттой)
            offset_account = None
            if offset_account_id:
                offset_account = ChartOfAccounts.objects.get(id=offset_account_id)
                
                # Эсрэг данс сонгосон бол мөнгөн гүйлгээний үзүүлэлт заавал сонгох
                if not cash_flow_indicator_id:
                    messages.error(request, 'Эсрэг данс сонгосон бол мөнгөн гүйлгээний үзүүлэлт заавал сонгоно уу.')
                    raise ValueError("Cash flow indicator required")
            
            # Сурагчийн төлбөрийн хуваарилалтын нийт дүн шалгах
            total_allocated = Decimal('0')
            if income_type == 'STUDENT_PAYMENT':
                i = 0
                while f'allocations[{i}][student]' in request.POST:
                    amount = request.POST.get(f'allocations[{i}][amount]')
                    if amount:
                        total_allocated += Decimal(amount)
                    i += 1
                
                # Нийт дүн тэнцүү эсэхийг шалгах
                if total_allocated > 0 and total_allocated != income_dec:
                    messages.error(request, 
                        f'Хуваарилалтын нийт дүн ({total_allocated:,.0f}₮) '
                        f'орлогын дүнтэй ({income_dec:,.0f}₮) тэнцүү байх ёстой.')
                    raise ValueError("Allocation amount mismatch")
            
            # Кассын гүйлгээ үүсгэх
            transaction = BankTransaction.objects.create(
                account_type='CASH',
                bank_name='CASH_REGISTER',
                bank_account=cash_account,
                transaction_date=transaction_date,
                income_amount=income_dec,
                expense_amount=expense_dec,
                description=description,
                offset_account=offset_account,
                cash_flow_indicator_id=cash_flow_indicator_id if cash_flow_indicator_id else None,
                income_type=income_type if income_type else '',
                expense_type=expense_type if expense_type else '',
                is_processed=False  # Эхлээд False, дараа нь журнал үүсгэсний дараа True болно
            )
            
            # Сурагчийн төлбөр бол allocations оруулах
            allocation_count = 0
            if income_type == 'STUDENT_PAYMENT':
                i = 0
                while f'allocations[{i}][student]' in request.POST:
                    student_id = request.POST.get(f'allocations[{i}][student]')
                    course_id = request.POST.get(f'allocations[{i}][course]')
                    month = request.POST.get(f'allocations[{i}][month]')
                    year = request.POST.get(f'allocations[{i}][year]')
                    amount = request.POST.get(f'allocations[{i}][amount]')
                    
                    if student_id and course_id and month and year and amount:
                        student = UserProfile.objects.get(id=student_id)
                        course = Course.objects.get(id=course_id)
                        
                        PaymentAllocation.objects.create(
                            transaction=transaction,
                            student=student,
                            course=course,
                            month=int(month),
                            year=int(year),
                            amount=Decimal(amount)
                        )
                        allocation_count += 1
                    i += 1
            
            # Эсрэг данс байвал журналд холбох, үгүй бол зөвхөн гүйлгээ хадгалах
            if offset_account:
                from .import_bank_transactions import regenerate_accounting_entries
                result = regenerate_accounting_entries([transaction], request.user)
                
                if result > 0:
                    if income_type == 'STUDENT_PAYMENT' and allocation_count > 0:
                        messages.success(request, 
                            f'Кассын орлого амжилттай бүртгэгдэж, журналд холбогдлоо '
                            f'({allocation_count} хуваарилалт).')
                    else:
                        messages.success(request, 'Кассын гүйлгээ амжилттай бүртгэгдэж, журналд холбогдлоо.')
                else:
                    messages.warning(request, 'Гүйлгээ бүртгэгдсэн боловч журнал үүсгэхэд алдаа гарлаа.')
            else:
                # Эсрэг данс байхгүй - зөвхөн гүйлгээ хадгалагдлаа
                if income_type == 'STUDENT_PAYMENT' and allocation_count > 0:
                    messages.success(request, 
                        f'Кассын орлого амжилттай бүртгэгдлээ ({allocation_count} хуваарилалт). '
                        f'Журналд холбохын тулд эсрэг данс сонгоод засна уу.')
                else:
                    messages.success(request, 
                        'Кассын гүйлгээ амжилттай бүртгэгдлээ. '
                        'Журналд холбохын тулд эсрэг данс сонгоод засна уу.')
            
            return redirect('main:cash_transaction_list')
            
        except ChartOfAccounts.DoesNotExist:
            messages.error(request, 'Сонгосон данс олдсонгүй.')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Сонгосон сурагч олдсонгүй.')
        except Course.DoesNotExist:
            messages.error(request, 'Сонгосон анги олдсонгүй.')
        except ValueError as e:
            # Validation алдаануудыг аль хэдийн messages-д нэмсэн
            pass
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    # GET request - форм харуулах
    # Кассын дансууд (100x, 101x код)
    from django.db.models import Q
    cash_accounts = ChartOfAccounts.objects.filter(
        Q(code__startswith='100') | Q(code__startswith='101'),
        is_active=True
    ).order_by('code')
    
    # Бүх идэвхтэй данс (эсрэг данс сонгох)
    accounts = ChartOfAccounts.objects.filter(is_active=True).order_by('code')
    
    # Мөнгөн гүйлгээний үзүүлэлтүүд
    cash_flow_indicators = CashFlowIndicator.objects.filter(is_active=True).order_by('code')
    
    # Сурагчид
    students = UserProfile.objects.filter(role=UserRole.STUDENT).order_by('first_name', 'last_name')
    
    context = {
        'cash_accounts': cash_accounts,
        'accounts': accounts,
        'cash_flow_indicators': cash_flow_indicators,
        'students': students,
        'income_types': BankTransaction.INCOME_TYPE_CHOICES,
        'expense_types': BankTransaction.EXPENSE_TYPE_CHOICES,
    }
    
    return render(request, 'main/cash_transaction_create.html', context)


@login_required
def cash_transaction_list(request):
    """Кассын гүйлгээний жагсаалт"""
    from django.core.paginator import Paginator
    
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан бодогч, менежер роль эсвэл касс харах эрхтэй
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        profile.role == 'MANAGER' or
        user.is_superuser or
        user.has_perm('main.view_banktransaction')
    )
    
    if not has_access:
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    # Зөвхөн кассын гүйлгээ
    transactions = BankTransaction.objects.filter(
        account_type='CASH'
    ).select_related(
        'bank_account', 'offset_account', 'income_sale',
        'accounting_entry__debit_account', 'accounting_entry__credit_account'
    ).prefetch_related(
        'allocations__student', 'allocations__course', 'sale_allocations__sale'
    ).order_by('-transaction_date', '-id')

    # Кассын дансаар шүүх
    cash_account_id = request.GET.get('cash_account')
    if cash_account_id:
        transactions = transactions.filter(bank_account_id=cash_account_id)
    
    # Огноогоор шүүх
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        transactions = transactions.filter(transaction_date__gte=date_from)
    if date_to:
        transactions = transactions.filter(transaction_date__lte=date_to)
    
    # Статистик
    total_count = transactions.count()
    total_income = transactions.aggregate(Sum('income_amount'))['income_amount__sum'] or 0
    total_expense = transactions.aggregate(Sum('expense_amount'))['expense_amount__sum'] or 0
    cash_balance = total_income - total_expense
    
    # Pagination
    paginator = Paginator(transactions, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Annotate each transaction on the current page with linked/unlinked document counts
    for tx in page_obj.object_list:
        try:
            alloc_count = tx.allocations.count()
        except Exception:
            alloc_count = 0
        try:
            sale_alloc_count = tx.sale_allocations.count()
        except Exception:
            sale_alloc_count = 0
        income_sale_flag = 1 if getattr(tx, 'income_sale_id', None) else 0
        accounting_flag = 1 if getattr(tx, 'accounting_entry_id', None) else 0

        tx.linked_docs_count = alloc_count + sale_alloc_count + income_sale_flag + accounting_flag

        # Determine if there's unlinked amount that could be allocated/linked
        try:
            available = tx.available_income_amount if getattr(tx, 'income_amount', 0) > 0 else 0
        except Exception:
            available = 0
        tx.unlinked_docs_count = 1 if available and available > 0 else 0

    # Aggregate counts: number of transactions that have any linked document, and number without
    from django.db.models import Q
    linked_tx_q = Q(allocations__isnull=False) | Q(sale_allocations__isnull=False) | Q(income_sale__isnull=False) | Q(accounting_entry__isnull=False)
    # distinct because joins may duplicate
    linked_tx_count = transactions.filter(linked_tx_q).distinct().count()
    unlinked_tx_count = total_count - linked_tx_count

    # Also keep earlier document-level aggregates if needed
    total_allocations = PaymentAllocation.objects.filter(transaction__in=transactions).count()
    total_sale_allocations = SalePaymentAllocation.objects.filter(transaction__in=transactions).count()
    total_income_sales = transactions.filter(income_sale__isnull=False).count()
    total_accounting = transactions.filter(accounting_entry__isnull=False).count()
    total_linked_docs = total_allocations + total_sale_allocations + total_income_sales + total_accounting

    # Count transactions that still have available income amount (unlinked potential per transaction)
    total_unlinked_docs = 0
    for t in transactions:
        try:
            if getattr(t, 'available_income_amount', 0) and t.available_income_amount > 0:
                total_unlinked_docs += 1
        except Exception:
            continue

    # Count transactions that are income vs expense
    income_tx_count = transactions.filter(income_amount__gt=0).count()
    expense_tx_count = transactions.filter(expense_amount__gt=0).count()

    # Кассын дансууд (100x, 101x код)
    from django.db.models import Q
    cash_accounts = ChartOfAccounts.objects.filter(
        Q(code__startswith='100') | Q(code__startswith='101'),
        is_active=True
    ).order_by('code')

    context = {
        'transactions': page_obj,
        'cash_accounts': cash_accounts,
        'total_count': total_count,
        'total_income': total_income,
        'total_expense': total_expense,
        'cash_balance': cash_balance,
        'page_obj': page_obj,
        'total_linked_docs': total_linked_docs,
        'total_unlinked_docs': total_unlinked_docs,
        'linked_tx_count': linked_tx_count,
        'unlinked_tx_count': unlinked_tx_count,
        'income_tx_count': income_tx_count,
        'expense_tx_count': expense_tx_count,
    }

    return render(request, 'main/cash_transaction_list.html', context)


@login_required
def cash_transaction_edit(request, transaction_id):
    """Кассын гүйлгээ засах"""
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан бодогч, Менежер бүлэг эсвэл касс засах эрхтэй
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.change_banktransaction')
    )
    
    if not has_access:
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    # Гүйлгээг авах
    transaction = get_object_or_404(BankTransaction, id=transaction_id, account_type='CASH')
    # Preserve return_to so we can redirect back to the same list page (pagination)
    return_to = request.GET.get('return_to', request.POST.get('return_to', '')).strip()

    # Автоматаар үүссэн эсрэг мөрийг эндээс засахыг хориглоно (эх гүйлгээнээс удирдана)
    if transaction.transfer_source_id:
        messages.error(
            request,
            'Энэ кассын гүйлгээ харилцахын гүйлгээний холболтоос автоматаар үүссэн тул '
            'эндээс засах боломжгүй. Эх банкны гүйлгээн дээрээ засна уу.'
        )
        return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction.transfer_source_id)

    # Одоо байгаа хуваарилалтууд
    existing_allocations = PaymentAllocation.objects.filter(transaction=transaction).select_related('student', 'course')

    # Prevent editing here if transaction is linked (journal, allocations, sale link)
    if transaction.accounting_entry or transaction.allocations.exists() or transaction.sale_allocations.exists() or transaction.income_sale_id:
        messages.error(request, 'Энэ кассын гүйлгээ ямар нэгэн баримт/журналтай холбогдсон тул эндээс засах боломжгүй. Холболтыг цуцалсны дараа засна уу.')
        return redirect('main:link_bank_transaction_to_journal', transaction_id=transaction_id)

    if request.method == 'POST':
        try:
            # Мэдээлэл цуглуулах
            transaction_date_str = request.POST.get('transaction_date')
            cash_account_code = request.POST.get('cash_account')
            income_amount = request.POST.get('income_amount') or 0
            expense_amount = request.POST.get('expense_amount') or 0
            description = request.POST.get('description')
            offset_account_id = request.POST.get('offset_account')
            income_type = request.POST.get('income_type')
            expense_type = request.POST.get('expense_type')
            cash_flow_indicator_id = request.POST.get('cash_flow_indicator')
            
            # Утга шалгах
            if not transaction_date_str or not cash_account_code or not description:
                messages.error(request, 'Огноо, кассын данс, тайлбар заавал бөглөнө үү.')
                raise ValueError("Required fields missing")
            
            # Огноог date объект болгох
            from datetime import datetime
            transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()
            
            # Орлого эсвэл зарлага заавал байх
            income_dec = Decimal(income_amount) if income_amount else Decimal('0')
            expense_dec = Decimal(expense_amount) if expense_amount else Decimal('0')
            
            if income_dec == 0 and expense_dec == 0:
                messages.error(request, 'Орлого эсвэл зарлага заавал бөглөнө үү.')
                raise ValueError("Amount required")
            
            if income_dec > 0 and expense_dec > 0:
                messages.error(request, 'Орлого эсвэл зарлага аль нэгийг л бөглөнө үү (хоёуланг биш).')
                raise ValueError("Both amounts entered")
            
            # Касс дансыг олох
            cash_account = ChartOfAccounts.objects.get(code=cash_account_code)
            
            # Эсрэг данс (сонголттой)
            offset_account = None
            if offset_account_id:
                offset_account = ChartOfAccounts.objects.get(id=offset_account_id)
                
                # Эсрэг данс сонгосон бол мөнгөн гүйлгээний үзүүлэлт заавал сонгох
                if not cash_flow_indicator_id:
                    messages.error(request, 'Эсрэг данс сонгосон бол мөнгөн гүйлгээний үзүүлэлт заавал сонгоно уу.')
                    raise ValueError("Cash flow indicator required")
            
            # Сурагчийн төлбөрийн хуваарилалтын нийт дүн шалгах
            total_allocated = Decimal('0')
            if income_type == 'STUDENT_PAYMENT':
                i = 0
                while f'allocations[{i}][student]' in request.POST:
                    amount = request.POST.get(f'allocations[{i}][amount]')
                    if amount:
                        total_allocated += Decimal(amount)
                    i += 1
                
                # Нийт дүн тэнцүү эсэхийг шалгах
                if total_allocated > 0 and total_allocated != income_dec:
                    messages.error(request, 
                        f'Хуваарилалтын нийт дүн ({total_allocated:,.0f}₮) '
                        f'орлогын дүнтэй ({income_dec:,.0f}₮) тэнцүү байх ёстой.')
                    raise ValueError("Allocation amount mismatch")
            
            # Хуучин журналыг устгах (шинээр үүсгэх гэж байгаа)
            if transaction.accounting_entry:
                old_entry = transaction.accounting_entry
                transaction.accounting_entry = None
                transaction.save()
                old_entry.delete()
            
            # Гүйлгээг шинэчлэх
            transaction.transaction_date = transaction_date
            transaction.bank_account = cash_account
            transaction.income_amount = income_dec
            transaction.expense_amount = expense_dec
            transaction.description = description
            transaction.offset_account = offset_account
            transaction.cash_flow_indicator_id = cash_flow_indicator_id if cash_flow_indicator_id else None
            transaction.income_type = income_type if income_type else ''
            transaction.expense_type = expense_type if expense_type else ''
            transaction.is_processed = False
            transaction.save()
            
            # Хуучин хуваарилалтуудыг устгах
            PaymentAllocation.objects.filter(transaction=transaction).delete()
            
            # Сурагчийн төлбөр бол шинэ allocations оруулах
            allocation_count = 0
            if income_type == 'STUDENT_PAYMENT':
                i = 0
                while f'allocations[{i}][student]' in request.POST:
                    student_id = request.POST.get(f'allocations[{i}][student]')
                    course_id = request.POST.get(f'allocations[{i}][course]')
                    month = request.POST.get(f'allocations[{i}][month]')
                    year = request.POST.get(f'allocations[{i}][year]')
                    amount = request.POST.get(f'allocations[{i}][amount]')
                    
                    if student_id and course_id and month and year and amount:
                        student = UserProfile.objects.get(id=student_id)
                        course = Course.objects.get(id=course_id)
                        
                        PaymentAllocation.objects.create(
                            transaction=transaction,
                            student=student,
                            course=course,
                            month=int(month),
                            year=int(year),
                            amount=Decimal(amount)
                        )
                        allocation_count += 1
                    i += 1
            
            # Эсрэг данс байвал журналд холбох
            if offset_account:
                from .import_bank_transactions import regenerate_accounting_entries
                result = regenerate_accounting_entries([transaction], request.user)
                
                if result > 0:
                    messages.success(request, 'Кассын гүйлгээ амжилттай засагдаж, журналд холбогдлоо.')
                else:
                    messages.warning(request, 'Гүйлгээ засагдсан боловч журнал үүсгэхэд алдаа гарлаа.')
            else:
                messages.success(request, 'Кассын гүйлгээ амжилттай засагдлаа. Журналд холбохын тулд эсрэг данс сонгоно уу.')
            
            return redirect('main:cash_transaction_list')
            
        except ChartOfAccounts.DoesNotExist:
            messages.error(request, 'Сонгосон данс олдсонгүй.')
        except UserProfile.DoesNotExist:
            messages.error(request, 'Сонгосон сурагч олдсонгүй.')
        except Course.DoesNotExist:
            messages.error(request, 'Сонгосон анги олдсонгүй.')
        except ValueError:
            pass
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    # GET request - форм харуулах
    from django.db.models import Q
    cash_accounts = ChartOfAccounts.objects.filter(
        Q(code__startswith='100') | Q(code__startswith='101'),
        is_active=True
    ).order_by('code')
    
    accounts = ChartOfAccounts.objects.filter(is_active=True).order_by('code')
    cash_flow_indicators = CashFlowIndicator.objects.filter(is_active=True).order_by('code')
    students = UserProfile.objects.filter(role=UserRole.STUDENT).order_by('first_name', 'last_name')
    
    context = {
        'transaction': transaction,
        'cash_accounts': cash_accounts,
        'accounts': accounts,
        'cash_flow_indicators': cash_flow_indicators,
        'students': students,
        'income_types': BankTransaction.INCOME_TYPE_CHOICES,
        'expense_types': BankTransaction.EXPENSE_TYPE_CHOICES,
        'existing_allocations': existing_allocations,
    }
    
    return render(request, 'main/cash_transaction_edit.html', context)


@login_required
def cash_transaction_delete(request, transaction_id):
    """Кассын гүйлгээ устгах"""
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах: админ, нягтлан бодогч, Менежер бүлэг эсвэл касс устгах эрхтэй
    has_access = (
        profile.is_admin or
        profile.is_accountant or
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.delete_banktransaction')
    )
    
    if not has_access:
        messages.error(request, 'Энэ үйлдэл хийх эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    # Гүйлгээг авах
    transaction = get_object_or_404(BankTransaction, id=transaction_id, account_type='CASH')
    
    if request.method == 'POST':
        # Автоматаар үүссэн эсрэг мөрийг шууд устгахыг хориглоно
        if transaction.transfer_source_id:
            messages.error(
                request,
                'Энэ кассын гүйлгээ харилцахын гүйлгээний холболтоос автоматаар үүссэн. '
                'Устгахын тулд эх банкны гүйлгээний холболтыг цуцлана уу.'
            )
            return redirect('main:cash_transaction_list')

        # Журналын бичилттэй холбогдсон бол устгахыг хориглоно
        if transaction.accounting_entry_id:
            messages.error(
                request,
                'Кассын гүйлгээ журналын бичилттэй холбогдсон байна. '
                'Эхлээд журналын холболтыг салгаж устга.'
            )
            return redirect('main:cash_transaction_list')

        if transaction.allocations.exists() or transaction.sale_allocations.exists():
            messages.error(
                request,
                'Кассын гүйлгээ хуваарилалттай холбогдсон байна. '
                'Эхлээд хуваарилалтыг устгаж устга.'
            )
            return redirect('main:cash_transaction_list')

        try:
            transaction.delete()
            messages.success(request, 'Кассын гүйлгээ амжилттай устгагдлаа.')
            return redirect('main:cash_transaction_list')
        except Exception as e:
            messages.error(request, f'Устгахад алдаа гарлаа: {str(e)}')
            return redirect('main:cash_transaction_list')

    # GET request - баталгаажуулах хуудас харуулах
    return render(request, 'main/cash_transaction_delete.html', {'transaction': transaction})


# ========================================
# БАРАА МАТЕРИАЛЫН ХУДАЛДАН АВАЛТ/БОРЛУУЛАЛТ
# ========================================

@login_required
def purchase_create(request):
    """Худалдан авалт бүртгэх - Журналтай холбогдсон"""
    from datetime import datetime
    profile = request.user.profile
    user = request.user
    
    # Админ, нягтлан, эсвэл эрхтэй (permission-based)
    has_access = (
        profile.is_admin or 
        profile.role == UserRole.ACCOUNTANT or 
        user.is_superuser or
        user.has_perm('main.add_purchase')
    )
    if not has_access:
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:inventory_list')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                product_id = request.POST.get('product', '').replace(',', '').strip()
                if not product_id:
                    raise Exception('Бараа сонгоно уу!')
                product = Product.objects.get(id=product_id)
                quantity = int(request.POST.get('quantity', '0').replace(',', ''))
                price = Decimal(request.POST.get('price', '0').replace(',', ''))
                if quantity <= 0:
                    raise Exception('Тоо ширхэг 0-ээс их байх ёстой!')
                payment_method = request.POST.get('payment_method')
                bank_account_id = request.POST.get('bank_account', '').replace(',', '').strip()
                counterparty_id = request.POST.get('counterparty', '').replace(',', '').strip()
                reference_number = request.POST.get('reference_number', '')
                notes = request.POST.get('notes', '')
                transaction_date_str = request.POST.get('transaction_date')
            
                total_amount = quantity * price
                transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()
                
                # 1. StockMovement үүсгэх
                movement = StockMovement(
                    product=product,
                    movement_type='IN',
                    quantity=quantity,
                    price=price,
                    payment_method=payment_method,
                    reference_number=reference_number,
                    notes=notes,
                    created_by=request.user
                )
            
                # 2. Харилцагч сонгосон бол холбох
                if counterparty_id:
                    counterparty = Counterparty.objects.get(id=counterparty_id)
                    movement.counterparty = counterparty
                    movement.customer_name = counterparty.name
                
                # 3. Төлбөр: Бэлэн эсвэл данс
                if payment_method in ['CASH', 'BANK']:
                    if not bank_account_id:
                        raise Exception('Касс/Банкны данс сонгону уу!')
                    bank_account = ChartOfAccounts.objects.get(id=bank_account_id)
                    movement.bank_account = bank_account
                
                    # Журналын бичилт үүсгэх
                    inventory_account = ChartOfAccounts.objects.filter(code='150101').first()
                    if not inventory_account:
                        raise Exception('150101-Бараа материал данс олдсонгүй!')
                    
                    _, entry_number = next_entry_number(
                        f"PUR-{transaction_date.strftime('%Y%m%d')}-"
                    )
                    
                    entry = AccountingEntry.objects.create(
                        entry_number=entry_number,
                        entry_date=transaction_date,
                        debit_account=inventory_account,
                        credit_account=bank_account,
                        debit_amount=total_amount,
                        credit_amount=total_amount,
                        description=f"Худалдан авалт: {product.name} x{quantity} - {reference_number}",
                        created_by=request.user
                    )
                    movement.accounting_entry = entry
                
                # 4. Зээлээр төлбөр
                elif payment_method == 'CREDIT' and counterparty_id:
                    counterparty = Counterparty.objects.get(id=counterparty_id)
                    counterparty.balance += total_amount
                    counterparty.save()
                    
                    inventory_account = ChartOfAccounts.objects.filter(code='150101').first()
                    payable_account = ChartOfAccounts.objects.filter(code='2101').first()
                    
                    if inventory_account and payable_account:
                        _, entry_number = next_entry_number(
                            f"PUR-{transaction_date.strftime('%Y%m%d')}-"
                        )
                        
                        entry = AccountingEntry.objects.create(
                            entry_number=entry_number,
                            entry_date=transaction_date,
                            debit_account=inventory_account,
                            credit_account=payable_account,
                            debit_amount=total_amount,
                            credit_amount=total_amount,
                            description=f"Худалдан авалт (зээлээр): {product.name} x{quantity} - {reference_number}",
                            created_by=request.user
                        )
                        movement.accounting_entry = entry
                
                movement.save()
                messages.success(request, f'Худалдан авалт амжилттай! Үлдэгдэл: {product.current_stock}')
                return redirect('main:stock_movement_list')
            
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    products = Product.objects.filter(is_active=True)
    cash_accounts = ChartOfAccounts.objects.filter(code__startswith='100', is_active=True)
    bank_accounts = ChartOfAccounts.objects.filter(code__startswith='110', is_active=True)
    suppliers = Counterparty.objects.filter(counterparty_type__in=['SUPPLIER', 'BOTH'], is_active=True)
    
    context = {
        'products': products,
        'cash_accounts': cash_accounts,
        'bank_accounts': bank_accounts,
        'suppliers': suppliers,
        'payment_methods': StockMovement.PAYMENT_METHOD_CHOICES,
    }
    return render(request, 'main/purchase_form.html', context)


@login_required
def purchase_create_multi(request):
    """Олон бараа худалдан авалт бүртгэх"""
    from datetime import datetime
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах
    has_access = (
        profile.is_admin or 
        profile.role == UserRole.ACCOUNTANT or 
        user.is_superuser or
        user.has_perm('main.add_purchase')
    )
    if not has_access:
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:inventory_list')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Ерөнхий мэдээлэл
                payment_method = request.POST.get('payment_method')
                bank_account_ids = [v for v in request.POST.getlist('bank_account') if v.strip()]
                bank_account_id = bank_account_ids[0].replace(',', '').strip() if bank_account_ids else ''
                counterparty_id = request.POST.get('counterparty', '').replace(',', '').strip()
                bank_transaction_id = request.POST.get('bank_transaction', '').replace(',', '').strip()
                reference_number = request.POST.get('reference_number', '')
                notes = request.POST.get('notes', '')
                transaction_date_str = request.POST.get('transaction_date')
                transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()
                
                # Барааны мэдээлэл боловсруулах
                product_ids = []
                row_num = 1
                while True:
                    product_key = f'product_{row_num}'
                    if product_key not in request.POST or not request.POST.get(product_key):
                        break
                    
                    product_id = request.POST.get(product_key, '').replace(',', '').strip()
                    quantity = int(request.POST.get(f'quantity_{row_num}', '0').replace(',', ''))
                    price = Decimal(request.POST.get(f'price_{row_num}', '0').replace(',', ''))
                    
                    if product_id and quantity > 0 and price > 0:
                        product_ids.append({
                            'product_id': product_id,
                            'quantity': quantity,
                            'price': price
                        })
                    
                    row_num += 1
                
                if not product_ids:
                    raise Exception('Дор хаяж 1 бараа нэмнэ үү!')
                
                # Нийлүүлэгч
                counterparty = None
                supplier_name = ''
                if counterparty_id:
                    counterparty = Counterparty.objects.get(id=counterparty_id)
                    supplier_name = counterparty.name
                
                # Бараа бүрийг бүртгэх
                total_expense = Decimal('0')
                movements_created = []
                
                for item in product_ids:
                    product = Product.objects.get(id=item['product_id'])
                    quantity = item['quantity']
                    price = item['price']
                    
                    item_total = quantity * price
                    total_expense += item_total
                    
                    # StockMovement үүсгэх
                    movement = StockMovement.objects.create(
                        product=product,
                        movement_type='IN',
                        quantity=quantity,
                        price=price,
                        payment_method=payment_method,
                        reference_number=reference_number,
                        notes=notes,
                        customer_name=supplier_name,
                        counterparty=counterparty,
                        created_by=request.user
                    )
                    movements_created.append(movement)
                
                # Журналын бичилт үүсгэх
                if payment_method in ['CASH', 'BANK']:
                    if not bank_account_id:
                        raise Exception('Касс/Банкны данс сонгоно уу!')
                    bank_account = ChartOfAccounts.objects.get(id=bank_account_id)
                    inventory_account = ChartOfAccounts.objects.filter(code='150101').first()
                    
                    if not inventory_account:
                        raise Exception('150101-Бараа материалын данс олдсонгүй!')
                    
                    _, entry_number = next_entry_number(
                        f"PUR-{transaction_date.strftime('%Y%m%d')}-"
                    )
                    
                    # Худалдан авалтын бичилт
                    entry = AccountingEntry.objects.create(
                        entry_number=entry_number,
                        entry_date=transaction_date,
                        debit_account=inventory_account,
                        credit_account=bank_account,
                        debit_amount=total_expense,
                        credit_amount=total_expense,
                        description=f"Худалдан авалт ({len(product_ids)} бараа) - {reference_number}",
                        created_by=request.user
                    )
                    
                    # Банкны гүйлгээтэй холбох
                    if bank_transaction_id:
                        try:
                            bank_txn = BankTransaction.objects.get(id=bank_transaction_id)
                            bank_txn.accounting_entry = entry
                            bank_txn.is_processed = True
                            bank_txn.save()
                        except BankTransaction.DoesNotExist:
                            pass
                    
                    # Эхний movement-д холбох
                    if movements_created:
                        movements_created[0].accounting_entry = entry
                        movements_created[0].bank_account = bank_account
                        movements_created[0].save()
                
                elif payment_method == 'CREDIT' and counterparty:
                    counterparty.balance += total_expense
                    counterparty.save()
                    
                    inventory_account = ChartOfAccounts.objects.filter(code='150101').first()
                    payable_account = ChartOfAccounts.objects.filter(code='2101').first()
                    
                    if inventory_account and payable_account:
                        _, entry_number = next_entry_number(
                            f"PUR-{transaction_date.strftime('%Y%m%d')}-"
                        )
                        
                        entry = AccountingEntry.objects.create(
                            entry_number=entry_number,
                            entry_date=transaction_date,
                            debit_account=inventory_account,
                            credit_account=payable_account,
                            debit_amount=total_expense,
                            credit_amount=total_expense,
                            description=f"Худалдан авалт зээлээр ({len(product_ids)} бараа) - {reference_number}",
                            created_by=request.user
                        )
                        
                        if movements_created:
                            movements_created[0].accounting_entry = entry
                            movements_created[0].save()
                
                messages.success(request, f'{len(product_ids)} бараа амжилттай худалдаж авлаа! Нийт: {total_expense:,.0f}₮')
                return redirect('main:purchase_list')
        
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    # Template-руу өгөгдөл дамжуулах
    products = Product.objects.filter(is_active=True)
    
    # JavaScript-д ашиглахад хялбар байдлаар products list үүсгэх
    import json
    products_json = json.dumps([
        {
            'id': p.id,
            'name': p.name,
            'purchase_price': float(p.purchase_price),
            'current_stock': p.current_stock
        }
        for p in products
    ], ensure_ascii=False)
    
    cash_accounts = ChartOfAccounts.objects.filter(code__startswith='100', is_active=True)
    bank_accounts = ChartOfAccounts.objects.filter(code__startswith='110', is_active=True)
    suppliers = Counterparty.objects.filter(counterparty_type__in=['SUPPLIER', 'BOTH'], is_active=True)
    
    # Холбогдоогүй банкны зарлагын гүйлгээнүүд
    unlinked_transactions = BankTransaction.objects.filter(
        expense_amount__gt=0,  # Зарлагын гүйлгээ
        accounting_entry__isnull=True  # Санхүүгийн бичилттэй холбогдоогүй
    ).select_related('bank_account').order_by('-transaction_date')[:100]  # Сүүлийн 100
    
    # JavaScript-д ашиглахад хялбар байдлаар transactions list үүсгэх
    transactions_json = json.dumps([
        {
            'id': t.id,
            'bank_account_id': t.bank_account.id if t.bank_account else None,
            'transaction_date': t.transaction_date.strftime('%Y-%m-%d'),
            'description': t.description,
            'expense_amount': float(t.expense_amount),
            'counterparty_name': t.counterparty_name or ''
        }
        for t in unlinked_transactions
    ], ensure_ascii=False)
    
    context = {
        'products': products,
        'products_json': products_json,
        'cash_accounts': cash_accounts,
        'bank_accounts': bank_accounts,
        'suppliers': suppliers,
        'payment_methods': StockMovement.PAYMENT_METHOD_CHOICES,
        'unlinked_transactions': unlinked_transactions,
        'transactions_json': transactions_json,
    }
    return render(request, 'main/purchase_form_multi.html', context)


@login_required
def purchase_edit(request, movement_id):
    """Худалдан авалт засах"""
    profile = request.user.profile
    user = request.user
    
    has_access = (
        profile.is_admin or 
        profile.role == UserRole.ACCOUNTANT or 
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.change_stockmovement')
    )
    if not has_access:
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:purchase_list')
    
    movement = get_object_or_404(StockMovement, id=movement_id, movement_type='IN')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Шинэ өгөгдөл
                quantity = int(request.POST.get('quantity'))
                price = Decimal(request.POST.get('price'))
                notes = request.POST.get('notes', '')
                
                # StockMovement шинэчлэх (current_stock @property тул автоматаар тооцоологдоно)
                movement.quantity = quantity
                movement.price = price
                movement.notes = notes
                movement.save()
                
                # Журналын бичилт шинэчлэх (хэрэв байвал)
                if movement.accounting_entry:
                    total_amount = quantity * price
                    movement.accounting_entry.debit_amount = total_amount
                    movement.accounting_entry.credit_amount = total_amount
                    movement.accounting_entry.description = f"Худалдан авалт (засварласан): {movement.product.name} x{quantity}"
                    movement.accounting_entry.save()
                
                messages.success(request, 'Худалдан авалт амжилттай засагдлаа!')
                return redirect('main:purchase_list')
                
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    context = {
        'movement': movement,
        'is_edit': True,
    }
    return render(request, 'main/purchase_edit.html', context)


@login_required
def purchase_delete(request, movement_id):
    """Худалдан авалт устгах"""
    profile = request.user.profile
    user = request.user
    
    has_access = (
        profile.is_admin or 
        profile.role == UserRole.ACCOUNTANT or 
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.delete_stockmovement')
    )
    if not has_access:
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:purchase_list')
    
    movement = get_object_or_404(StockMovement, id=movement_id, movement_type='IN')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # current_stock нь @property тул тусад нь өөрчлөх шаардлагагүй —
                # StockMovement устсаны дараа автоматаар тооцоологдоно.
                movement.delete()
                
                messages.success(request, 'Худалдан авалт амжилттай устгагдлаа!')
                return redirect('main:purchase_list')
                
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    context = {'movement': movement}
    return render(request, 'main/purchase_delete.html', context)


def _get_salesperson_display_name(user):
    if not user:
        return ''

    try:
        if user.profile.mongolian_name:
            return user.profile.mongolian_name
    except Exception:
        pass

    return user.get_full_name() or user.username


def _get_sale_payment_method_label(payment_method):
    return {
        'CASH': 'Касс',
        'BANK': 'Харилцах',
        'BANK_PENDING': 'Харилцах',
        'CREDIT': 'Зээлээр',
    }.get(payment_method, '')


def _resolve_sale_counterparty(counterparty_id, customer_name_manual):
    """Борлуулалтын харилцагчийг dropdown эсвэл гараас бичсэн нэрээс шийднэ."""
    customer_name_manual = (customer_name_manual or '').strip()

    if counterparty_id:
        counterparty = Counterparty.objects.get(id=counterparty_id)
        return counterparty, counterparty.name

    if not customer_name_manual:
        return None, ''

    counterparty, created = Counterparty.objects.get_or_create(
        name=customer_name_manual,
        defaults={
            'counterparty_type': 'CUSTOMER',
            'is_active': True,
        }
    )

    update_fields = []
    if counterparty.counterparty_type == 'SUPPLIER':
        counterparty.counterparty_type = 'BOTH'
        update_fields.append('counterparty_type')
    if not counterparty.is_active:
        counterparty.is_active = True
        update_fields.append('is_active')
    if update_fields:
        counterparty.save(update_fields=update_fields)

    return counterparty, counterparty.name


def _create_sale_record(*, transaction_date, counterparty, salesperson, notes,
                        payment_method, created_by, items, bank_transaction=None):
    total_amount = sum(item['quantity'] * item['price'] for item in items)
    # BANK_PENDING: мөнгө ирээгүй, дараа банкаас холбоно
    paid_amount = total_amount if payment_method in ['CASH', 'BANK'] else Decimal('0')

    sale = Sale.objects.create(
        customer=counterparty,
        sale_date=transaction_date,
        status='PAID' if paid_amount >= total_amount and total_amount > 0 else 'DRAFT',
        total_amount=total_amount,
        paid_amount=paid_amount,
        payment_date=transaction_date if paid_amount > 0 else None,
        notes=notes,
        salesperson_name=_get_salesperson_display_name(salesperson),
        expected_payment_method=_get_sale_payment_method_label(payment_method),
        created_by=created_by,
    )

    for item in items:
        SaleItem.objects.create(
            sale=sale,
            product=item['product'],
            quantity=item['quantity'],
            unit_price=item['price'],
        )

    if bank_transaction:
        bank_transaction.income_sale = sale
        if not bank_transaction.income_type:
            bank_transaction.income_type = 'PRODUCT_SALE'
        bank_transaction.save()

    return sale


@login_required
def sale_create(request):
    """Борлуулалт бүртгэх - Журналтай холбогдсон"""
    from datetime import datetime
    profile = request.user.profile
    user = request.user
    
    # Админ, нягтлан, эсвэл эрхтэй (permission-based)
    has_access = (
        profile.is_admin or 
        profile.role == UserRole.ACCOUNTANT or 
        user.is_superuser or
        user.has_perm('main.add_sale')
    )
    if not has_access:
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:inventory_list')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                product_id = request.POST.get('product', '').replace(',', '').strip()
                if not product_id:
                    raise Exception('Бараа сонгоно уу!')
                product = Product.objects.get(id=product_id)
                quantity = int(request.POST.get('quantity', '0').replace(',', ''))
                price = Decimal(request.POST.get('price', '0').replace(',', ''))
                if quantity <= 0:
                    raise Exception('Тоо ширхэг 0-ээс их байх ёстой!')
                payment_method = request.POST.get('payment_method')
                bank_account_ids = [v for v in request.POST.getlist('bank_account') if v.strip()]
                bank_account_id = bank_account_ids[0].replace(',', '').strip() if bank_account_ids else ''
                counterparty_id = request.POST.get('counterparty', '').replace(',', '').strip()
                customer_name_manual = request.POST.get('customer_name_manual', '').strip()
                reference_number = request.POST.get('reference_number', '')
                notes = request.POST.get('notes', '')
                salesperson_id = request.POST.get('salesperson', '').replace(',', '').strip()
                transaction_date_str = request.POST.get('transaction_date')
                
                total_amount = quantity * price
                transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()
                
                if product.current_stock < quantity:
                    raise Exception(f'Үлдэгдэл хүрэлцэхгүй! Одоо: {product.current_stock}')
                
                movement = StockMovement(
                    product=product,
                    movement_type='OUT',
                    quantity=quantity,
                    price=price,
                    payment_method=payment_method,
                    reference_number=reference_number,
                    notes=notes,
                    created_by=request.user
                )
                
                counterparty, customer_name = _resolve_sale_counterparty(
                    counterparty_id=counterparty_id,
                    customer_name_manual=customer_name_manual,
                )
                if counterparty:
                    movement.counterparty = counterparty
                movement.customer_name = customer_name
                
                if salesperson_id:
                    salesperson = User.objects.get(id=salesperson_id)
                    movement.salesperson = salesperson
                
                if payment_method in ['CASH', 'BANK']:
                    if not bank_account_id:
                        raise Exception('Касс/Банкны данс сонгоно уу!')
                    bank_account = ChartOfAccounts.objects.get(id=bank_account_id)
                    movement.bank_account = bank_account
                    
                    revenue_account = ChartOfAccounts.objects.filter(code='510101').first()
                    if not revenue_account:
                        raise Exception('510101-Борлуулалтын орлого данс олдсонгүй!')
                    
                    _, entry_number = next_entry_number(
                        f"SALE-{transaction_date.strftime('%Y%m%d')}-"
                    )
                    
                    entry = AccountingEntry.objects.create(
                        entry_number=entry_number,
                        entry_date=transaction_date,
                        debit_account=bank_account,
                        credit_account=revenue_account,
                        debit_amount=total_amount,
                        credit_amount=total_amount,
                        description=f"Борлуулалт: {product.name} x{quantity} - {reference_number}",
                        created_by=request.user
                    )
                    movement.accounting_entry = entry
                    
                    # Өртөг бичилт
                    cost_of_goods = quantity * product.purchase_price
                    inventory_account = ChartOfAccounts.objects.filter(code='150101').first()
                    cogs_account = ChartOfAccounts.objects.filter(code='5101').first()
                    
                    if inventory_account and cogs_account:
                        AccountingEntry.objects.create(
                            entry_number=f"{entry_number}-COGS",
                            entry_date=transaction_date,
                            debit_account=cogs_account,
                            credit_account=inventory_account,
                            debit_amount=cost_of_goods,
                            credit_amount=cost_of_goods,
                            description=f"Борлуулалтын өртөг: {product.name} - {reference_number}",
                            created_by=request.user
                        )
                    
                elif payment_method == 'CREDIT' and counterparty_id:
                    counterparty = Counterparty.objects.get(id=counterparty_id)
                    counterparty.balance -= total_amount
                    counterparty.save()
                    
                    receivable_account = ChartOfAccounts.objects.filter(code='1201').first()
                    revenue_account = ChartOfAccounts.objects.filter(code='510101').first()
                    
                    if receivable_account and revenue_account:
                        _, entry_number = next_entry_number(
                            f"SALE-{transaction_date.strftime('%Y%m%d')}-"
                        )
                        
                        entry = AccountingEntry.objects.create(
                            entry_number=entry_number,
                            entry_date=transaction_date,
                            debit_account=receivable_account,
                            credit_account=revenue_account,
                            debit_amount=total_amount,
                            credit_amount=total_amount,
                            description=f"Борлуулалт (зээлээр): {product.name} x{quantity} | {reference_number}",
                            created_by=request.user
                        )
                        movement.accounting_entry = entry
                        
                        cost_of_goods = quantity * product.purchase_price
                        inventory_account = ChartOfAccounts.objects.filter(code='150101').first()
                        cogs_account = ChartOfAccounts.objects.filter(code='5101').first()
                        
                        if inventory_account and cogs_account:
                            AccountingEntry.objects.create(
                                entry_number=f"{entry_number}-COGS",
                                entry_date=transaction_date,
                                debit_account=cogs_account,
                                credit_account=inventory_account,
                                debit_amount=cost_of_goods,
                                credit_amount=cost_of_goods,
                                description=f"Борлуулалтын өртөг: {product.name} | {reference_number}",
                                created_by=request.user
                            )

                sale = _create_sale_record(
                    transaction_date=transaction_date,
                    counterparty=movement.counterparty,
                    salesperson=movement.salesperson,
                    notes=notes,
                    payment_method=payment_method,
                    created_by=request.user,
                    items=[{
                        'product': product,
                        'quantity': quantity,
                        'price': price,
                    }],
                )
                
                movement.save()
                messages.success(request, f'Борлуулалт амжилттай! Үлдэгдэл: {product.current_stock}')
                return redirect('main:sale_detail', sale_id=sale.id)
            
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    products = Product.objects.filter(is_active=True)
    cash_accounts = ChartOfAccounts.objects.filter(code__startswith='100', is_active=True)
    bank_accounts = ChartOfAccounts.objects.filter(code__startswith='110', is_active=True)
    customers = Counterparty.objects.filter(counterparty_type__in=['CUSTOMER', 'BOTH'], is_active=True)
    
    # Менежер эрхтэй хэрэглэгчдийн жагсаалт (борлуулагч)
    manager_users = UserProfile.objects.filter(
        role__in=[UserRole.PRESIDENT, UserRole.DIRECTOR, UserRole.MANAGER]
    ).select_related('user')
    
    context = {
        'products': products,
        'cash_accounts': cash_accounts,
        'bank_accounts': bank_accounts,
        'customers': customers,
        'manager_users': manager_users,
        'payment_methods': StockMovement.PAYMENT_METHOD_CHOICES,
    }
    return render(request, 'main/sale_form.html', context)


@login_required
def sale_create_multi(request):
    """Олон бараа борлуулалт бүртгэх"""
    from datetime import datetime
    profile = request.user.profile
    user = request.user
    
    # Эрх шалгах
    has_access = (
        profile.is_admin or 
        profile.role == UserRole.ACCOUNTANT or 
        user.is_superuser or
        user.has_perm('main.add_sale')
    )
    if not has_access:
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:inventory_list')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Ерөнхий мэдээлэл
                payment_method = request.POST.get('payment_method')
                bank_account_ids = [v for v in request.POST.getlist('bank_account') if v.strip()]
                bank_account_id = bank_account_ids[0].replace(',', '').strip() if bank_account_ids else ''
                counterparty_id = request.POST.get('counterparty', '').replace(',', '').strip()
                salesperson_id = request.POST.get('salesperson', '').replace(',', '').strip()
                bank_transaction_id = request.POST.get('bank_transaction', '').replace(',', '').strip()
                reference_number = request.POST.get('reference_number', '')
                notes = request.POST.get('notes', '')
                transaction_date_str = request.POST.get('transaction_date')
                transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()
                
                # Барааны мэдээлэл боловсруулах
                product_ids = []
                row_num = 1
                while True:
                    product_key = f'product_{row_num}'
                    if product_key not in request.POST or not request.POST.get(product_key):
                        break
                    
                    product_id = request.POST.get(product_key, '').replace(',', '').strip()
                    quantity = int(request.POST.get(f'quantity_{row_num}', '0').replace(',', ''))
                    price = Decimal(request.POST.get(f'price_{row_num}', '0').replace(',', ''))
                    
                    if product_id and quantity > 0 and price > 0:
                        product_ids.append({
                            'product_id': product_id,
                            'quantity': quantity,
                            'price': price
                        })
                    
                    row_num += 1
                
                if not product_ids:
                    raise Exception('Дор хаяж 1 бараа нэмнэ үү!')
                
                # Борлуулагч
                salesperson = None
                if salesperson_id:
                    salesperson = User.objects.get(id=salesperson_id)
                
                # Үйлчлүүлэгч
                customer_name_manual = request.POST.get('customer_name_manual', '').strip()
                counterparty, customer_name = _resolve_sale_counterparty(
                    counterparty_id=counterparty_id,
                    customer_name_manual=customer_name_manual,
                )
                
                # Бараа бүрийг бүртгэх
                total_revenue = Decimal('0')
                total_cost = Decimal('0')
                movements_created = []
                sale_items = []
                
                for item in product_ids:
                    product = Product.objects.get(id=item['product_id'])
                    quantity = item['quantity']
                    price = item['price']
                    
                    # Үлдэгдэл шалгах
                    if product.current_stock < quantity:
                        raise Exception(f'{product.name}: Үлдэгдэл хүрэлцэхгүй! Одоо: {product.current_stock}')
                    
                    item_total = quantity * price
                    total_revenue += item_total
                    total_cost += quantity * product.purchase_price
                    sale_items.append({
                        'product': product,
                        'quantity': quantity,
                        'price': price,
                    })
                    
                    # StockMovement үүсгэх
                    movement = StockMovement.objects.create(
                        product=product,
                        movement_type='OUT',
                        quantity=quantity,
                        price=price,
                        payment_method=payment_method,
                        reference_number=reference_number,
                        notes=notes,
                        customer_name=customer_name,
                        counterparty=counterparty,
                        salesperson=salesperson,
                        created_by=request.user
                    )
                    movements_created.append(movement)

                bank_transaction = None
                if bank_transaction_id:
                    try:
                        bank_transaction = BankTransaction.objects.get(id=bank_transaction_id)
                    except BankTransaction.DoesNotExist:
                        bank_transaction = None

                sale = _create_sale_record(
                    transaction_date=transaction_date,
                    counterparty=counterparty,
                    salesperson=salesperson,
                    notes=notes,
                    payment_method=payment_method,
                    created_by=request.user,
                    items=sale_items,
                    bank_transaction=bank_transaction,
                )
                
                # Журналын бичилт үүсгэх
                if payment_method in ['CASH', 'BANK']:
                    if not bank_account_id:
                        raise Exception('Касс/Банкны данс сонгоно уу!')
                    bank_account = ChartOfAccounts.objects.get(id=bank_account_id)
                    revenue_account = ChartOfAccounts.objects.filter(code='510101').first()
                    
                    if not revenue_account:
                        raise Exception('510101-Борлуулалтын орлого данс олдсонгүй!')
                    
                    _, entry_number = next_entry_number(
                        f"SALE-{transaction_date.strftime('%Y%m%d')}-"
                    )
                    
                    # Орлогын бичилт
                    entry = AccountingEntry.objects.create(
                        entry_number=entry_number,
                        entry_date=transaction_date,
                        debit_account=bank_account,
                        credit_account=revenue_account,
                        debit_amount=total_revenue,
                        credit_amount=total_revenue,
                        description=f"Борлуулалт ({len(product_ids)} бараа) - {reference_number}",
                        created_by=request.user
                    )
                    
                    # Банкны гүйлгээтэй холбох
                    if bank_transaction:
                        bank_transaction.accounting_entry = entry
                        bank_transaction.is_processed = True
                        bank_transaction.save()
                    
                    # Эхний movement-д холбох
                    if movements_created:
                        movements_created[0].accounting_entry = entry
                        movements_created[0].bank_account = bank_account
                        movements_created[0].save()
                    
                    # Өртөг бичилт
                    inventory_account = ChartOfAccounts.objects.filter(code='150101').first()
                    cogs_account = ChartOfAccounts.objects.filter(code='5101').first()
                    
                    if inventory_account and cogs_account:
                        AccountingEntry.objects.create(
                            entry_number=f"{entry_number}-COGS",
                            entry_date=transaction_date,
                            debit_account=cogs_account,
                            credit_account=inventory_account,
                            debit_amount=total_cost,
                            credit_amount=total_cost,
                            description=f"Борлуулалтын өртөг ({len(product_ids)} бараа) - {reference_number}",
                            created_by=request.user
                        )
                
                elif payment_method == 'CREDIT' and counterparty:
                    counterparty.balance -= total_revenue
                    counterparty.save()
                    
                    receivable_account = ChartOfAccounts.objects.filter(code='1201').first()
                    revenue_account = ChartOfAccounts.objects.filter(code='510101').first()
                    
                    if receivable_account and revenue_account:
                        _, entry_number = next_entry_number(
                            f"SALE-{transaction_date.strftime('%Y%m%d')}-"
                        )
                        
                        entry = AccountingEntry.objects.create(
                            entry_number=entry_number,
                            entry_date=transaction_date,
                            debit_account=receivable_account,
                            credit_account=revenue_account,
                            debit_amount=total_revenue,
                            credit_amount=total_revenue,
                            description=f"Борлуулалт зээлээр ({len(product_ids)} бараа) - {reference_number}",
                            created_by=request.user
                        )
                        
                        if movements_created:
                            movements_created[0].accounting_entry = entry
                            movements_created[0].save()
                        
                        # Өртөг
                        inventory_account = ChartOfAccounts.objects.filter(code='150101').first()
                        cogs_account = ChartOfAccounts.objects.filter(code='5101').first()
                        
                        if inventory_account and cogs_account:
                            AccountingEntry.objects.create(
                                entry_number=f"{entry_number}-COGS",
                                entry_date=transaction_date,
                                debit_account=cogs_account,
                                credit_account=inventory_account,
                                debit_amount=total_cost,
                                credit_amount=total_cost,
                                description=f"Борлуулалтын өртөг ({len(product_ids)} бараа) - {reference_number}",
                                created_by=request.user
                            )
                
                elif payment_method == 'BANK_PENDING':
                    # Харилцахаар хожим орно — журнал үүсгэхгүй, банкны гүйлгээнд хожим холбоно
                    # Зөвхөн өртгийн бичилт хийнэ (агуулах бараа гарсан)
                    inventory_account = ChartOfAccounts.objects.filter(code='150101').first()
                    cogs_account = ChartOfAccounts.objects.filter(code='5101').first()
                    if inventory_account and cogs_account:
                        _, cogs_stem = next_entry_number(
                            f"SALE-{transaction_date.strftime('%Y%m%d')}-"
                        )
                        cogs_number = f"{cogs_stem}-COGS"
                        AccountingEntry.objects.create(
                            entry_number=cogs_number,
                            entry_date=transaction_date,
                            debit_account=cogs_account,
                            credit_account=inventory_account,
                            debit_amount=total_cost,
                            credit_amount=total_cost,
                            description=f"Борлуулалтын өртөг ({len(product_ids)} бараа) - {reference_number}",
                            created_by=request.user
                        )

                # Нэмэлт хуваарилалт (SaleExtraSplit) хадгалах + журнал үүсгэх
                # (модель устгагдсан байж болно — тиймээс хамгаалалттай)
                try:
                    from .models import SaleExtraSplit, BankTransactionSplit
                except Exception:
                    SaleExtraSplit = None
                    BankTransactionSplit = None
                split_index = 0
                while SaleExtraSplit:
                    acct_id = request.POST.get(f'sale_splits[{split_index}][account]', '').strip()
                    amt_raw = request.POST.get(f'sale_splits[{split_index}][amount]', '').replace(',', '').strip()
                    desc = request.POST.get(f'sale_splits[{split_index}][description]', '').strip()
                    if not acct_id and not amt_raw:
                        break
                    split_index += 1
                    if acct_id and amt_raw:
                        try:
                            split_amt = Decimal(amt_raw)
                            if split_amt > 0:
                                split_acct = ChartOfAccounts.objects.get(id=acct_id)
                                ses = SaleExtraSplit.objects.create(
                                    sale=sale,
                                    account=split_acct,
                                    amount=split_amt,
                                    description=desc,
                                )
                                # BANK төлбөрийн аргаар банкны гүйлгээтэй холбосон бол
                                # нэмэлт split-д тус бүр AccountingEntry үүсгэнэ
                                if bank_transaction and payment_method == 'BANK':
                                    _, split_stem = next_entry_number(
                                        f"SALE-{transaction_date.strftime('%Y%m%d')}-"
                                    )
                                    split_entry_number = f"{split_stem}-SPL"
                                    split_entry = AccountingEntry.objects.create(
                                        entry_number=split_entry_number,
                                        entry_date=transaction_date,
                                        debit_account=bank_account,
                                        credit_account=split_acct,
                                        debit_amount=split_amt,
                                        credit_amount=split_amt,
                                        description=desc or f"Nemelt huvaarilalt - {reference_number}",
                                        created_by=request.user,
                                    )
                                    BankTransactionSplit.objects.get_or_create(
                                        transaction=bank_transaction,
                                        account=split_acct,
                                        defaults={
                                            'amount': split_amt,
                                            'description': desc,
                                            'accounting_entry': split_entry,
                                        },
                                    )
                        except Exception:
                            pass

                messages.success(request, f'{len(product_ids)} бараа амжилттай борлуулагдлаа! Нийт: {total_revenue:,.0f}₮')
                return redirect('main:sale_detail', sale_id=sale.id)
        
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    # Template-руу өгөгдөл дамжуулах
    products = Product.objects.filter(is_active=True)
    
    # JavaScript-д ашиглахад хялбар байдлаар products list үүсгэх
    import json
    products_json = json.dumps([
        {
            'id': p.id,
            'name': p.name,
            'selling_price': float(p.selling_price),
            'current_stock': p.current_stock
        }
        for p in products
    ], ensure_ascii=False)
    
    cash_accounts = ChartOfAccounts.objects.filter(code__startswith='100', is_active=True)
    bank_accounts = ChartOfAccounts.objects.filter(code__startswith='110', is_active=True)
    all_accounts = ChartOfAccounts.objects.filter(is_active=True).order_by('code')
    customers = Counterparty.objects.filter(counterparty_type__in=['CUSTOMER', 'BOTH'], is_active=True)
    manager_users = UserProfile.objects.filter(
        role__in=[UserRole.PRESIDENT, UserRole.DIRECTOR, UserRole.MANAGER]
    ).select_related('user')
    
    # Холбогдоогүй банкны орлогын гүйлгээнүүд
    unlinked_transactions = BankTransaction.objects.filter(
        income_amount__gt=0,  # Орлогын гүйлгээ
        accounting_entry__isnull=True  # Санхүүгийн бичилттэй холбогдоогүй
    ).select_related('bank_account').order_by('-transaction_date')[:100]  # Сүүлийн 100
    
    # JavaScript-д ашиглахад хялбар байдлаар transactions list үүсгэх
    transactions_json = json.dumps([
        {
            'id': t.id,
            'bank_account_id': t.bank_account.id if t.bank_account else None,
            'transaction_date': t.transaction_date.strftime('%Y-%m-%d'),
            'description': t.description,
            'income_amount': float(t.income_amount),
            'counterparty_name': t.counterparty_name or ''
        }
        for t in unlinked_transactions
    ], ensure_ascii=False)
    
    context = {
        'products': products,
        'products_json': products_json,
        'cash_accounts': cash_accounts,
        'bank_accounts': bank_accounts,
        'all_accounts': all_accounts,
        'customers': customers,
        'manager_users': manager_users,
        'payment_methods': StockMovement.PAYMENT_METHOD_CHOICES,
        'unlinked_transactions': unlinked_transactions,
        'transactions_json': transactions_json,
    }
    return render(request, 'main/sale_form_multi.html', context)


@login_required
def sale_edit(request, movement_id):
    """Борлуулалт засах"""
    profile = request.user.profile
    user = request.user
    
    has_access = (
        profile.is_admin or 
        profile.role == UserRole.ACCOUNTANT or 
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.change_stockmovement')
    )
    if not has_access:
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:sale_list')
    
    movement = get_object_or_404(StockMovement, id=movement_id, movement_type='OUT')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                old_quantity = movement.quantity
                
                # Шинэ өгөгдөл
                quantity = int(request.POST.get('quantity'))
                price = Decimal(request.POST.get('price'))
                notes = request.POST.get('notes', '')
                
                # Шинэ үлдэгдэл шалгах:
                # current_stock нь хуучин movement-г тооцсон тул
                # current_stock + old_quantity = боломжит нийт үлдэгдэл
                available = movement.product.current_stock + old_quantity
                if available < quantity:
                    raise Exception(f'Үлдэгдэл хүрэлцэхгүй! Боломжтой: {available}')
                
                # StockMovement шинэчлэх (current_stock @property тул автоматаар тооцоологдоно)
                movement.quantity = quantity
                movement.price = price
                movement.notes = notes
                movement.save()
                
                # Журналын бичилт шинэчлэх (хэрэв байвал)
                if movement.accounting_entry:
                    total_amount = quantity * price
                    movement.accounting_entry.debit_amount = total_amount
                    movement.accounting_entry.credit_amount = total_amount
                    movement.accounting_entry.description = f"Борлуулалт (засварласан): {movement.product.name} x{quantity}"
                    movement.accounting_entry.save()
                
                messages.success(request, 'Борлуулалт амжилттай засагдлаа!')
                return redirect('main:sale_list')
                
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    context = {
        'movement': movement,
        'is_edit': True,
    }
    return render(request, 'main/sale_edit.html', context)


@login_required
def sale_delete(request, movement_id):
    """Борлуулалт устгах"""
    profile = request.user.profile
    user = request.user
    
    has_access = (
        profile.is_admin or 
        profile.role == UserRole.ACCOUNTANT or 
        user.is_superuser or
        user.groups.filter(name='Менежер').exists() or
        user.has_perm('main.delete_stockmovement')
    )
    if not has_access:
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:sale_list')
    
    movement = get_object_or_404(StockMovement, id=movement_id, movement_type='OUT')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # current_stock нь @property тул тусад нь өөрчлөх шаардлагагүй —
                # StockMovement устсаны дараа автоматаар тооцоологдоно.
                movement.delete()
                
                messages.success(request, 'Борлуулалт амжилттай устгагдлаа!')
                return redirect('main:sale_list')
                
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    context = {'movement': movement}
    return render(request, 'main/sale_delete.html', context)


# ===================== БАРААНЫ ТАЙЛАНГУУД =====================

@login_required
def inventory_summary_quantity(request):
    """Барааны товчоо тайлан - тоо ширхэгээр"""
    user = request.user
    has_access = (
        user.profile.is_admin or 
        user.profile.is_accountant or
        user.groups.filter(name='Менежер').exists() or
        user.groups.filter(name='Харагч').exists()
    )
    if not has_access:
        messages.error(request, 'Та энэ хуудсыг үзэх эрхгүй байна.')
        return redirect('main:dashboard')
    
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    products = Product.objects.filter(is_active=True).select_related('category')
    
    # Нийт худалдан авалт болон борлуулалтын тоо ширхэг
    report_data = []
    for product in products:
        purchases_qs = StockMovement.objects.filter(product=product, movement_type='IN')
        sales_qs = StockMovement.objects.filter(product=product, movement_type='OUT')
        
        if date_from:
            purchases_qs = purchases_qs.filter(created_at__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
            sales_qs = sales_qs.filter(created_at__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
        if date_to:
            purchases_qs = purchases_qs.filter(created_at__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
            sales_qs = sales_qs.filter(created_at__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
        
        purchases = purchases_qs.aggregate(total=Sum('quantity'))['total'] or 0
        sales = sales_qs.aggregate(total=Sum('quantity'))['total'] or 0
        
        report_data.append({
            'product': product,
            'total_purchased': purchases,
            'total_sold': sales,
            'current_stock': product.current_stock,
        })
    
    context = {
        'report_data': report_data,
        'report_title': 'Барааны товчоо тайлан - Тоо ширхэг',
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'main/inventory_summary_quantity.html', context)


@login_required
def inventory_summary_sales(request):
    """Барааны товчоо тайлан - борлуулалтын үнийн дүн"""
    user = request.user
    has_access = (
        user.profile.is_admin or 
        user.profile.is_accountant or
        user.groups.filter(name='Менежер').exists() or
        user.groups.filter(name='Харагч').exists()
    )
    if not has_access:
        messages.error(request, 'Та энэ хуудсыг үзэх эрхгүй байна.')
        return redirect('main:dashboard')
    
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    products = Product.objects.filter(is_active=True).select_related('category')
    
    report_data = []
    for product in products:
        sales_qs = StockMovement.objects.filter(product=product, movement_type='OUT')
        
        if date_from:
            sales_qs = sales_qs.filter(created_at__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
        if date_to:
            sales_qs = sales_qs.filter(created_at__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
        
        sales = sales_qs.aggregate(
            total_quantity=Sum('quantity'),
            total_amount=Sum(F('quantity') * F('price'))
        )
        
        report_data.append({
            'product': product,
            'total_quantity': sales['total_quantity'] or 0,
            'total_amount': sales['total_amount'] or Decimal('0'),
            'avg_price': (sales['total_amount'] / sales['total_quantity']) if sales['total_quantity'] else Decimal('0'),
        })
    
    # Нийт дүн
    grand_total = sum(item['total_amount'] for item in report_data)
    
    context = {
        'report_data': report_data,
        'grand_total': grand_total,
        'report_title': 'Барааны товчоо тайлан - Борлуулалтын дүн',
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'main/inventory_summary_sales.html', context)


@login_required
def inventory_summary_purchases(request):
    """Барааны товчоо тайлан - худалдан авалтын үнийн дүн"""
    user = request.user
    has_access = (
        user.profile.is_admin or 
        user.profile.is_accountant or
        user.groups.filter(name='Менежер').exists() or
        user.groups.filter(name='Харагч').exists()
    )
    if not has_access:
        messages.error(request, 'Та энэ хуудсыг үзэх эрхгүй байна.')
        return redirect('main:dashboard')
    
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    products = Product.objects.filter(is_active=True).select_related('category')
    
    report_data = []
    for product in products:
        purchases_qs = StockMovement.objects.filter(product=product, movement_type='IN')
        
        if date_from:
            purchases_qs = purchases_qs.filter(created_at__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
        if date_to:
            purchases_qs = purchases_qs.filter(created_at__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
        
        purchases = purchases_qs.aggregate(
            total_quantity=Sum('quantity'),
            total_amount=Sum(F('quantity') * F('price'))
        )
        
        report_data.append({
            'product': product,
            'total_quantity': purchases['total_quantity'] or 0,
            'total_amount': purchases['total_amount'] or Decimal('0'),
            'avg_price': (purchases['total_amount'] / purchases['total_quantity']) if purchases['total_quantity'] else Decimal('0'),
        })
    
    # Нийт дүн
    grand_total = sum(item['total_amount'] for item in report_data)
    
    context = {
        'report_data': report_data,
        'grand_total': grand_total,
        'report_title': 'Барааны товчоо тайлан - Худалдан авалтын дүн',
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'main/inventory_summary_purchases.html', context)


@login_required
def inventory_balance_report(request):
    """Үлдэгдлийн тайлан - огнооны хооронд шүүнэ"""
    user = request.user
    has_access = (
        user.profile.is_admin or 
        user.profile.is_accountant or
        user.groups.filter(name='Менежер').exists() or
        user.groups.filter(name='Харагч').exists()
    )
    if not has_access:
        messages.error(request, 'Та энэ хуудсыг үзэх эрхгүй байна.')
        return redirect('main:dashboard')
    
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    products = Product.objects.filter(is_active=True).select_related('category')
    
    report_data = []
    for product in products:
        # Эхний үлдэгдэл = initial_stock + хугацааны өмнөх бүх хөдөлгөөн
        opening_balance = product.initial_stock
        if date_from:
            movements_before = StockMovement.objects.filter(
                product=product,
                created_at__lt=datetime.strptime(date_from, '%Y-%m-%d').date()
            )
            # Орлого (IN, RETURN)
            income_before = movements_before.filter(
                movement_type__in=['IN', 'RETURN']
            ).aggregate(total=Sum('quantity'))['total'] or 0
            # Зарлага (OUT)
            expense_before = movements_before.filter(
                movement_type='OUT'
            ).aggregate(total=Sum('quantity'))['total'] or 0
            # Тохируулга (ADJUSTMENT)
            adjustment_before = movements_before.filter(
                movement_type='ADJUSTMENT'
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            opening_balance = product.initial_stock + income_before - expense_before + adjustment_before
        
        # Тухайн хугацааны хөдөлгөөн
        movements = StockMovement.objects.filter(product=product)
        if date_from:
            movements = movements.filter(created_at__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
        if date_to:
            movements = movements.filter(created_at__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
        
        # Орлого (IN, RETURN)
        income_movements = movements.filter(movement_type__in=['IN', 'RETURN'])
        purchases = income_movements.aggregate(
            total_quantity=Sum('quantity'),
            total_amount=Sum(F('quantity') * F('price'))
        )
        
        # Зарлага (OUT)
        expense_movements = movements.filter(movement_type='OUT')
        sales = expense_movements.aggregate(
            total_quantity=Sum('quantity'),
            total_amount=Sum(F('quantity') * F('price'))
        )
        
        # Тохируулга (ADJUSTMENT)
        adjustment_movements = movements.filter(movement_type='ADJUSTMENT')
        adjustments = adjustment_movements.aggregate(
            total_quantity=Sum('quantity')
        )
        
        # Эцсийн үлдэгдэл
        closing_balance = opening_balance + (purchases['total_quantity'] or 0) - (sales['total_quantity'] or 0) + (adjustments['total_quantity'] or 0)
        
        # Үнийн дүн тооцоолох (борлуулах үнээр)
        opening_amount = opening_balance * product.selling_price if product.selling_price else Decimal('0')
        closing_amount = closing_balance * product.selling_price if product.selling_price else Decimal('0')
        
        report_data.append({
            'product': product,
            'opening_balance': opening_balance,
            'opening_amount': opening_amount,
            'purchased_qty': purchases['total_quantity'] or 0,
            'purchased_amount': purchases['total_amount'] or Decimal('0'),
            'sold_qty': sales['total_quantity'] or 0,
            'sold_amount': sales['total_amount'] or Decimal('0'),
            'closing_balance': closing_balance,
            'closing_amount': closing_amount,
        })
    
    # Багануудын нийт дүн (хөл дүн)
    totals = {
        'opening_balance': sum(item['opening_balance'] for item in report_data),
        'opening_amount': sum(item['opening_amount'] for item in report_data),
        'purchased_qty': sum(item['purchased_qty'] for item in report_data),
        'purchased_amount': sum(item['purchased_amount'] for item in report_data),
        'sold_qty': sum(item['sold_qty'] for item in report_data),
        'sold_amount': sum(item['sold_amount'] for item in report_data),
        'closing_balance': sum(item['closing_balance'] for item in report_data),
        'closing_amount': sum(item['closing_amount'] for item in report_data),
    }
    
    context = {
        'report_data': report_data,
        'totals': totals,
        'date_from': date_from,
        'date_to': date_to,
        'report_title': 'Үлдэгдлийн тайлан',
    }
    return render(request, 'main/inventory_balance_report.html', context)


@login_required
def bank_statement_report(request):
    """Банкны хуулгын тайлан - огноо, банк, холбоосоор шүүнэ"""
    user = request.user
    has_access = (
        user.profile.is_admin or
        user.profile.is_accountant or
        user.groups.filter(name='Менежер').exists() or
        user.groups.filter(name='Харагч').exists() or
        user.is_superuser or
        user.has_perm('main.view_banktransaction')
    )
    if not has_access:
        messages.error(request, 'Та энэ хуудсыг үзэх эрхгүй байна.')
        return redirect('main:dashboard')

    # Шүүлтүүрийн утгууд
    bank_account_id = request.GET.get('bank_account', '')
    is_linked = request.GET.get('is_linked', '')   # 'all', 'linked', 'unlinked'
    date_from_str = request.GET.get('date_from', '')
    date_to_str = request.GET.get('date_to', '')

    # Зөвхөн банкны гүйлгээ
    base_qs = BankTransaction.objects.filter(
        account_type='BANK'
    ).select_related('bank_account', 'offset_account')

    # Банкны дансаар шүүх
    if bank_account_id:
        base_qs = base_qs.filter(bank_account_id=bank_account_id)

    # Холбоосоор шүүх
    if is_linked == 'linked':
        base_qs = base_qs.filter(accounting_entry__isnull=False)
    elif is_linked == 'unlinked':
        base_qs = base_qs.filter(accounting_entry__isnull=True)

    # Огноогоор шүүх
    date_from = None
    date_to = None
    qs = base_qs
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
            qs = qs.filter(transaction_date__gte=date_from)
        except ValueError:
            date_from_str = ''
    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
            qs = qs.filter(transaction_date__lte=date_to)
        except ValueError:
            date_to_str = ''

    # Данс тус бүрийн тухайн хугацааны эхний үлдэгдэл тооцоолох
    # Эхний үлдэгдэл = Дансны opening_balance + хугацаанаас өмнөх цэвэр урсгал
    opening_before_period = {}
    if date_from:
        prev_transactions = base_qs.filter(
            transaction_date__lt=date_from
        ).values('bank_account_id', 'income_amount', 'expense_amount')
        for prev_tx in prev_transactions:
            account_id = prev_tx['bank_account_id']
            income = prev_tx['income_amount'] or Decimal('0')
            expense = prev_tx['expense_amount'] or Decimal('0')
            opening_before_period[account_id] = opening_before_period.get(account_id, Decimal('0')) + income - expense

    # Хуулгын форматаар боловсруулах: гүйлгээ бүрт эхний үлдэгдэл, эцсийн үлдэгдлийг
    # гүйлгээний дарааллаар динамикаар тооцно.
    transactions = list(qs.order_by('transaction_date', 'id'))
    report_rows = []
    running_balances = {}
    for tx in transactions:
        account_id = tx.bank_account_id

        if account_id not in running_balances:
            account_opening = tx.bank_account.opening_balance or Decimal('0')
            account_opening += opening_before_period.get(account_id, Decimal('0'))
            running_balances[account_id] = account_opening

        row_opening = running_balances[account_id]
        income_amount = tx.income_amount or Decimal('0')
        expense_amount = tx.expense_amount or Decimal('0')
        row_closing = row_opening + income_amount - expense_amount
        running_balances[account_id] = row_closing

        report_rows.append({
            'tx': tx,
            'opening': row_opening,
            'income': income_amount,
            'expense': expense_amount,
            'closing': row_closing,
        })

    # Нийт дүн
    total_income = sum(r['income'] for r in report_rows)
    total_expense = sum(r['expense'] for r in report_rows)
    total_count = len(report_rows)
    linked_count = sum(1 for r in report_rows if r['tx'].accounting_entry_id)
    unlinked_count = total_count - linked_count

    # Банкны дансуудын жагсаалт (dropdown-д)
    bank_accounts = ChartOfAccounts.objects.filter(
        banktransaction__isnull=False
    ).distinct().order_by('code')

    context = {
        'report_rows': report_rows,
        'total_income': total_income,
        'total_expense': total_expense,
        'total_count': total_count,
        'linked_count': linked_count,
        'unlinked_count': unlinked_count,
        'bank_accounts': bank_accounts,
        'selected_bank': bank_account_id,
        'selected_linked': is_linked,
        'date_from': date_from_str,
        'date_to': date_to_str,
    }
    return render(request, 'main/bank_statement_report.html', context)


# ===================== ХАРИЛЦАГЧ УДИРДЛАГА =====================

@login_required
def counterparty_list(request):
    """Харилцагчийн жагсаалт"""
    user = request.user
    has_access = (
        user.profile.is_admin or 
        user.profile.is_accountant or
        user.groups.filter(name='Менежер').exists()
    )
    if not has_access:
        messages.error(request, 'Та энэ хуудсыг үзэх эрхгүй байна.')
        return redirect('main:dashboard')
    
    # Шүүлт
    search = request.GET.get('search', '')
    counterparty_type = request.GET.get('type', '')
    
    counterparties = Counterparty.objects.all().order_by('name')
    
    if search:
        counterparties = counterparties.filter(
            Q(name__icontains=search) |
            Q(contact_person__icontains=search) |
            Q(phone__icontains=search)
        )
    
    if counterparty_type:
        counterparties = counterparties.filter(counterparty_type=counterparty_type)
    
    context = {
        'counterparties': counterparties,
        'search': search,
        'counterparty_type': counterparty_type,
        'type_choices': Counterparty.COUNTERPARTY_TYPE_CHOICES,
    }
    return render(request, 'main/counterparty_list.html', context)


@login_required
def counterparty_create(request):
    """Харилцагч бүртгэх"""
    user = request.user
    has_access = (
        user.profile.is_admin or 
        user.profile.is_accountant or
        user.groups.filter(name='Менежер').exists()
    )
    if not has_access:
        messages.error(request, 'Та энэ хуудсыг үзэх эрхгүй байна.')
        return redirect('main:dashboard')
    
    if request.method == 'POST':
        try:
            counterparty = Counterparty.objects.create(
                name=request.POST.get('name'),
                counterparty_type=request.POST.get('counterparty_type', 'BOTH'),
                contact_person=request.POST.get('contact_person', ''),
                phone=request.POST.get('phone', ''),
                email=request.POST.get('email', ''),
                address=request.POST.get('address', ''),
                registration_number=request.POST.get('registration_number', ''),
                tax_number=request.POST.get('tax_number', ''),
            )
            messages.success(request, f'Харилцагч "{counterparty.name}" амжилттай бүртгэгдлээ!')
            return redirect('main:counterparty_list')
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    context = {
        'type_choices': Counterparty.COUNTERPARTY_TYPE_CHOICES,
    }
    return render(request, 'main/counterparty_form.html', context)


@login_required
def counterparty_edit(request, counterparty_id):
    """Харилцагч засах"""
    user = request.user
    has_access = (
        user.profile.is_admin or 
        user.profile.is_accountant or
        user.groups.filter(name='Менежер').exists()
    )
    if not has_access:
        messages.error(request, 'Та энэ хуудсыг үзэх эрхгүй байна.')
        return redirect('main:dashboard')
    
    counterparty = get_object_or_404(Counterparty, id=counterparty_id)
    
    if request.method == 'POST':
        try:
            counterparty.name = request.POST.get('name')
            counterparty.counterparty_type = request.POST.get('counterparty_type', 'BOTH')
            counterparty.contact_person = request.POST.get('contact_person', '')
            counterparty.phone = request.POST.get('phone', '')
            counterparty.email = request.POST.get('email', '')
            counterparty.address = request.POST.get('address', '')
            counterparty.registration_number = request.POST.get('registration_number', '')
            counterparty.tax_number = request.POST.get('tax_number', '')
            counterparty.save()
            
            messages.success(request, f'Харилцагч "{counterparty.name}" амжилттай засагдлаа!')
            return redirect('main:counterparty_list')
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    context = {
        'counterparty': counterparty,
        'type_choices': Counterparty.COUNTERPARTY_TYPE_CHOICES,
        'is_edit': True,
    }
    return render(request, 'main/counterparty_form.html', context)


@login_required
def counterparty_delete(request, counterparty_id):
    """Харилцагч устгах"""
    user = request.user
    has_access = (
        user.profile.is_admin or 
        user.profile.is_accountant or
        user.groups.filter(name='Менежер').exists()
    )
    if not has_access:
        messages.error(request, 'Та энэ хуудсыг үзэх эрхгүй байна.')
        return redirect('main:dashboard')
    
    counterparty = get_object_or_404(Counterparty, id=counterparty_id)
    
    if request.method == 'POST':
        try:
            name = counterparty.name
            counterparty.delete()
            messages.success(request, f'Харилцагч "{name}" устгагдлаа.')
            return redirect('main:counterparty_list')
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    context = {
        'counterparty': counterparty,
    }
    return render(request, 'main/counterparty_confirm_delete.html', context)


@login_required
def user_management(request):
    """Хэрэглэгчдийн удирдлага - зөвхөн админ"""
    if not (request.user.is_superuser or request.user.profile.is_admin):
        messages.error(request, 'Та энэ хуудсыг үзэх эрхгүй байна.')
        return redirect('main:dashboard')
    
    # Хайлт ба шүүлт
    users = User.objects.select_related('profile').prefetch_related('groups').all()
    
    search = request.GET.get('search', '').strip()
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(profile__mongolian_name__icontains=search) |
            Q(profile__phone__icontains=search) |
            Q(email__icontains=search)
        )
    
    role = request.GET.get('role', '').strip()
    if role:
        users = users.filter(profile__role=role)
    
    status = request.GET.get('status', '').strip()
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'staff':
        users = users.filter(is_staff=True)
    elif status == 'superuser':
        users = users.filter(is_superuser=True)
    
    # Pagination
    paginator = Paginator(users, 20)
    page = request.GET.get('page', 1)
    users = paginator.get_page(page)
    
    return render(request, 'main/user_management.html', {'users': users})


@login_required
def user_edit(request, user_id):
    """Хэрэглэгчийн эрх тохируулах"""
    if not (request.user.is_superuser or request.user.profile.is_admin):
        messages.error(request, 'Та энэ хуудсыг үзэх эрхгүй байна.')
        return redirect('main:dashboard')
    
    user_to_edit = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        try:
            # Django эрхүүд
            user_to_edit.is_superuser = 'is_superuser' in request.POST
            user_to_edit.is_staff = 'is_staff' in request.POST
            user_to_edit.is_active = 'is_active' in request.POST
            user_to_edit.save()
            
            # Роль
            new_role = request.POST.get('role')
            if new_role in dict(UserRole.choices):
                user_to_edit.profile.role = new_role
                user_to_edit.profile.save()
            
            # Бүлгүүд
            selected_groups = request.POST.getlist('groups')
            user_to_edit.groups.clear()
            for group_id in selected_groups:
                try:
                    group = Group.objects.get(id=group_id)
                    user_to_edit.groups.add(group)
                except Group.DoesNotExist:
                    pass
            
            messages.success(request, f'"{user_to_edit.username}"-ийн эрх амжилттай шинэчлэгдлээ!')
            return redirect('main:user_management')
            
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    available_groups = Group.objects.all().order_by('name')
    
    context = {
        'user_to_edit': user_to_edit,
        'available_groups': available_groups,
    }
    return render(request, 'main/user_edit.html', context)


# ============================================================
# GROUP MANAGEMENT VIEWS
# ============================================================

@login_required
def group_list(request):
    """Бүлгүүдийн жагсаалт - Админ хэрэглэгчид зориулсан"""
    # Зөвхөн админ хэрэглэгч үзэх эрхтэй
    if not (request.user.is_superuser or request.user.profile.is_admin):
        messages.error(request, 'Зөвхөн админ хэрэглэгч бүлэг удирдах эрхтэй.')
        return redirect('main:dashboard')
    
    groups = Group.objects.all().order_by('name').prefetch_related('permissions', 'user_set')
    
    context = {
        'groups': groups,
    }
    return render(request, 'main/group_list.html', context)


@login_required
def group_create(request):
    """Шинэ бүлэг үүсгэх"""
    # Зөвхөн админ хэрэглэгч үүсгэх эрхтэй
    if not (request.user.is_superuser or request.user.profile.is_admin):
        messages.error(request, 'Зөвхөн админ хэрэглэгч бүлэг үүсгэх эрхтэй.')
        return redirect('main:dashboard')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        permission_ids = request.POST.getlist('permissions')
        
        if not name:
            messages.error(request, 'Бүлгийн нэр оруулна уу.')
            return redirect('main:group_create')
        
        # Check if group name already exists
        if Group.objects.filter(name=name).exists():
            messages.error(request, f'"{name}" нэртэй бүлэг аль хэдийн байна.')
            return redirect('main:group_create')
        
        # Create group
        group = Group.objects.create(name=name)
        
        # Add permissions
        if permission_ids:
            permissions = Permission.objects.filter(id__in=permission_ids)
            group.permissions.set(permissions)
        
        messages.success(request, f'✓ "{name}" бүлэг амжилттай үүсгэгдлээ. ({len(permission_ids)} эрх оногдсон)')
        return redirect('main:group_list')
    
    # GET request - show form
    permissions = Permission.objects.all().select_related('content_type').order_by('content_type__app_label', 'codename')
    
    context = {
        'permissions': permissions,
        'is_edit': False,
    }
    return render(request, 'main/group_form.html', context)


@login_required
def group_edit(request, group_id):
    """Бүлэг засах"""
    # Зөвхөн админ хэрэглэгч засах эрхтэй
    if not (request.user.is_superuser or request.user.profile.is_admin):
        messages.error(request, 'Зөвхөн админ хэрэглэгч бүлэг засах эрхтэй.')
        return redirect('main:dashboard')
    
    group = get_object_or_404(Group, id=group_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        permission_ids = request.POST.getlist('permissions')
        
        if not name:
            messages.error(request, 'Бүлгийн нэр оруулна уу.')
            return redirect('main:group_edit', group_id=group_id)
        
        # Check if new name already exists (except current group)
        if Group.objects.filter(name=name).exclude(id=group_id).exists():
            messages.error(request, f'"{name}" нэртэй бүлэг аль хэдийн байна.')
            return redirect('main:group_edit', group_id=group_id)
        
        # Update group
        group.name = name
        group.save()
        
        # Update permissions
        permissions = Permission.objects.filter(id__in=permission_ids) if permission_ids else []
        group.permissions.set(permissions)
        
        messages.success(request, f'✓ "{name}" бүлэг амжилттай шинэчлэгдлээ. ({len(permission_ids)} эрх оногдсон)')
        return redirect('main:group_list')
    
    # GET request - show form
    permissions = Permission.objects.all().select_related('content_type').order_by('content_type__app_label', 'codename')
    
    context = {
        'group': group,
        'permissions': permissions,
        'is_edit': True,
    }
    return render(request, 'main/group_form.html', context)


@login_required
def group_delete(request, group_id):
    """Бүлэг устгах"""
    # Зөвхөн админ хэрэглэгч устгах эрхтэй
    if not (request.user.is_superuser or request.user.profile.is_admin):
        messages.error(request, 'Зөвхөн админ хэрэглэгч бүлэг устгах эрхтэй.')
        return redirect('main:dashboard')
    
    group = get_object_or_404(Group, id=group_id)
    
    if request.method == 'POST':
        group_name = group.name
        user_count = group.user_set.count()
        
        # Delete group
        group.delete()
        
        messages.success(request, f'✓ "{group_name}" бүлэг устгагдлав. ({user_count} хэрэглэгч нөлөөлөгдсөн)')
        return redirect('main:group_list')
    
    # GET request - show confirmation page
    context = {
        'group': group,
    }
    return render(request, 'main/group_confirm_delete.html', context)


@login_required
def role_info(request):
    """Роль-ын мэдээлэл харах - Бүх нэвтэрсэн хэрэглэгч"""
    from collections import Counter
    
    # Count users by role
    role_counts = Counter(UserProfile.objects.values_list('role', flat=True))
    
    role_stats = {
        'PRESIDENT': role_counts.get('PRESIDENT', 0),
        'DIRECTOR': role_counts.get('DIRECTOR', 0),
        'MANAGER': role_counts.get('MANAGER', 0),
        'ACCOUNTANT': role_counts.get('ACCOUNTANT', 0),
        'TEACHER_BEGINNER': role_counts.get('TEACHER_BEGINNER', 0),
        'TEACHER_INTERMEDIATE': role_counts.get('TEACHER_INTERMEDIATE', 0),
        'TEACHER_ADVANCED': role_counts.get('TEACHER_ADVANCED', 0),
        'STUDENT': role_counts.get('STUDENT', 0),
    }
    
    # Get users by role (for optional display)
    users_by_role = {}
    for role_code in role_stats.keys():
        users = UserProfile.objects.filter(role=role_code).select_related('user')[:10]
        users_by_role[role_code] = users
    
    context = {
        'role_stats': role_stats,
        'users_by_role': users_by_role,
    }
    return render(request, 'main/role_info.html', context)


def vision(request):
    return render(request, 'main/vision.html') # эсвэл таны зориулсан template нэр

def leadership(request):
    return render(request, 'main/leadership.html') # эсвэл таны зориулсан template нэр

def ethics(request):
    return render(request, 'main/ethics.html') # эсвэл таны зориулсан template нэр

def product_detail(request, product_id):
    return render(request, 'main/product_detail.html') # эсвэл таны зориулсан template нэр


def gallery(request):
    return render(request, 'main/gallery.html') # эсвэл таны зориулсан template нэр


def donate(request):
    return render(request, 'main/donate.html') # эсвэл таны зориулсан template нэр