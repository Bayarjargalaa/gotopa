from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import (
    UserProfile, Course, Enrollment, Attendance, UserRole, PageContent,
    Product, ProductCategory, StockMovement,
    Account, Counterparty, Transaction, Purchase, PurchaseItem, Sale, SaleItem,
    ChartOfAccounts, AccountingEntry, BankTransaction, CashFlowIndicator, PaymentAllocation
)
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Sum, Count
from django.utils import timezone
from decimal import Decimal
import re
import os
from .import_counterparties import import_counterparties
from .import_bank_transactions import import_bank_transactions

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
        mongolian_name = request.POST.get('mongolian_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        birth_date = request.POST.get('birth_date', '').strip()
        gender = request.POST.get('gender', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        
        # Validation
        errors = []
        
        if not mongolian_name:
            errors.append('Монгол нэр оруулна уу.')
        
        if not phone_number:
            errors.append('Утасны дугаар оруулна уу.')
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
            return render(request, 'main/register.html')
        
        try:
            # Username үүсгэх - утасны сүүлийн 8 орон
            username = f"student_{phone_clean[-8:]}"
            
            # Username давхцаж байгаа эсэх
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Энэ утасны дугаараар бүртгэл үүссэн байна.')
                return render(request, 'main/register.html')
            
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
                mongolian_name=mongolian_name,
                phone=phone_clean,
                address=address,
                birth_date=birth_date if birth_date else None,
                gender=gender if gender else None,
                role=UserRole.STUDENT,  # Автоматаар сурагч
                is_active_student=True,
            )
            
            # Автоматаар нэвтрүүлэх - backend зааж өгөх
            login(request, user, backend='main.backends.PhoneOrEmailBackend')
            messages.success(request, f'Тавтай морил, {mongolian_name}! Та амжилттай бүртгүүллээ.')
            return redirect('main:dashboard')
            
        except Exception as e:
            messages.error(request, f'Бүртгэл үүсгэхэд алдаа гарлаа: {str(e)}')
            return render(request, 'main/register.html')
    
    return render(request, 'main/register.html')
    messages.info(request, 'Амжилттай гарлаа.')
    return redirect('main:home')

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
        
    # Багш - өөрийн заадаг хичээлүүд
    elif profile.is_teacher:
        context['my_courses'] = Course.objects.filter(teacher=profile, is_active=True)
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
    """Сурагчдын жагсаалт - Зөвхөн админ болон багш"""
    if not (request.user.profile.is_admin or request.user.profile.is_teacher):
        messages.error(request, 'Хандах эрхгүй байна.')
        return redirect('main:dashboard')
    
    students = UserProfile.objects.filter(role=UserRole.STUDENT).select_related('user').prefetch_related('enrollments__course')
    return render(request, 'main/students.html', {'students': students})

@login_required
def student_create(request):
    """Сурагч бүртгэх - Зөвхөн админ"""
    if not request.user.profile.is_admin:
        messages.error(request, 'Танд сурагч бүртгэх эрх байхгүй байна.')
        return redirect('main:student_list')
    
    # Идэвхтэй сургалтууд
    courses = Course.objects.filter(is_active=True).order_by('-start_date')
    
    if request.method == 'POST':
        # Форм мэдээлэл авах
        mongolian_name = request.POST.get('mongolian_name', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        enrollment_date = request.POST.get('enrollment_date', '').strip()
        
        # Validation
        if not mongolian_name:
            messages.error(request, 'Нэр оруулна уу.')
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
            )
            
            # Нэрийг first_name, last_name болгох
            name_parts = mongolian_name.split()
            if name_parts:
                user.first_name = name_parts[0]
                if len(name_parts) > 1:
                    user.last_name = ' '.join(name_parts[1:])
                user.save()
            
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
                mongolian_name=mongolian_name,
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
                        # Суудал шалгах
                        if course.available_slots > 0:
                            Enrollment.objects.create(
                                student=student_profile,
                                course=course,
                                status='APPROVED',
                                is_active=True
                            )
                            enrolled_courses.append(course.name)
                    except Course.DoesNotExist:
                        pass
            
            success_msg = f'✓ Сурагч "{mongolian_name}" амжилттай бүртгэгдлээ!\nUsername: {username}\nНууц үг: {phone_clean[-8:] if len(phone_clean) >= 8 else phone_clean}'
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
    """Сурагч засах - Зөвхөн админ"""
    if not request.user.profile.is_admin:
        messages.error(request, 'Танд сурагч засах эрх байхгүй байна.')
        return redirect('main:student_list')
    
    student_profile = get_object_or_404(UserProfile, id=student_id, role=UserRole.STUDENT)
    
    # Идэвхтэй сургалтууд болон одоогийн бүртгэлүүд
    courses = Course.objects.filter(is_active=True).order_by('-start_date')
    enrollments = Enrollment.objects.filter(student=student_profile).select_related('course')
    enrolled_course_ids = list(enrollments.values_list('course_id', flat=True))
    
    if request.method == 'POST':
        # Форм мэдээлэл авах
        mongolian_name = request.POST.get('mongolian_name', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        birth_date = request.POST.get('birth_date', '').strip()
        gender = request.POST.get('gender', '').strip()
        city = request.POST.get('city', '').strip()
        district = request.POST.get('district', '').strip()
        address = request.POST.get('address', '').strip()
        notes = request.POST.get('notes', '').strip()
        enrollment_date = request.POST.get('enrollment_date', '').strip()
        photo = request.FILES.get('photo')
        is_active = request.POST.get('is_active') == 'on'
        
        # Validation
        if not mongolian_name:
            messages.error(request, 'Нэр оруулна уу.')
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
            name_parts = mongolian_name.split()
            if name_parts:
                user.first_name = name_parts[0]
                if len(name_parts) > 1:
                    user.last_name = ' '.join(name_parts[1:])
                else:
                    user.last_name = ''
            user.email = email if email else ''
            user.save()
            
            # UserProfile шинэчлэх
            from datetime import date
            student_profile.mongolian_name = mongolian_name
            student_profile.phone = phone_clean
            student_profile.birth_date = birth_date if birth_date else None
            student_profile.gender = gender if gender else ''
            student_profile.city = city
            student_profile.district = district
            student_profile.address = address
            student_profile.notes = notes
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
            new_course_ids = request.POST.getlist('new_courses')
            added_courses = []
            if new_course_ids:
                for course_id in new_course_ids:
                    try:
                        course = Course.objects.get(id=course_id, is_active=True)
                        # Аль хэдийн бүртгэгдсэн эсэх шалгах
                        if not Enrollment.objects.filter(student=student_profile, course=course).exists():
                            if course.available_slots > 0:
                                Enrollment.objects.create(
                                    student=student_profile,
                                    course=course,
                                    status='APPROVED',
                                    is_active=True
                                )
                                added_courses.append(course.name)
                    except Course.DoesNotExist:
                        pass
            
            success_msg = f'✓ Сурагч "{mongolian_name}" амжилттай шинэчлэгдлээ!'
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
    """Сурагч устгах - Зөвхөн админ"""
    if not request.user.profile.is_admin:
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
    ).select_related('user')
    return render(request, 'main/teacher_list.html', {'teachers': teachers})

@login_required
def teacher_create(request):
    """Багш бүртгэх - Зөвхөн админ"""
    if not request.user.profile.is_admin:
        messages.error(request, 'Танд багш бүртгэх эрх байхгүй байна.')
        return redirect('main:teacher_list')
    
    if request.method == 'POST':
        # Форм мэдээлэл авах
        mongolian_name = request.POST.get('mongolian_name', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        role = request.POST.get('role', '')
        
        # Validation
        if not mongolian_name:
            messages.error(request, 'Нэр оруулна уу.')
            return render(request, 'main/teacher_create.html')
        
        if not phone:
            messages.error(request, 'Утасны дугаар оруулна уу.')
            return render(request, 'main/teacher_create.html')
        
        if not role or role not in ['TEACHER_BEGINNER', 'TEACHER_INTERMEDIATE', 'TEACHER_ADVANCED']:
            messages.error(request, 'Багшийн түвшин сонгоно уу.')
            return render(request, 'main/teacher_create.html')
        
        # Утасны дугаар цэвэрлэх
        phone_clean = phone.replace(' ', '').replace('-', '').replace('+976', '')
        
        # Утасны дугаарын формат шалгах
        if not re.match(r'^\d{8}$', phone_clean):
            messages.error(request, 'Утасны дугаар 8 оронтой тоо байх ёстой. Жишээ: 99001234')
            return render(request, 'main/teacher_create.html')
        
        # Утас давхцаж байгаа эсэх шалгах
        if UserProfile.objects.filter(phone=phone_clean).exists():
            messages.error(request, f'Утасны дугаар {phone_clean} аль хэдийн бүртгэгдсэн байна.')
            return render(request, 'main/teacher_create.html')
        
        # Имэйл давхцаж байгаа эсэх шалгах
        if email and User.objects.filter(email=email).exists():
            messages.error(request, f'Имэйл хаяг {email} аль хэдийн бүртгэгдсэн байна.')
            return render(request, 'main/teacher_create.html')
        
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
                email=email if email else '',
                password=phone_clean[-8:] if len(phone_clean) >= 8 else phone_clean
            )
            
            # Нэрийг first_name, last_name болгох
            name_parts = mongolian_name.split()
            if name_parts:
                user.first_name = name_parts[0]
                if len(name_parts) > 1:
                    user.last_name = ' '.join(name_parts[1:])
                user.save()
            
            # UserProfile үүсгэх
            UserProfile.objects.create(
                user=user,
                mongolian_name=mongolian_name,
                phone=phone_clean,
                address=address,
                role=role,
                enrollment_date=timezone.now().date()
            )
            
            messages.success(
                request, 
                f'✓ Багш "{mongolian_name}" амжилттай бүртгэгдлээ!\n'
                f'Username: {username}\n'
                f'Нууц үг: {phone_clean[-8:] if len(phone_clean) >= 8 else phone_clean}'
            )
            return redirect('main:teacher_list')
            
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
            return render(request, 'main/teacher_create.html')
    
    return render(request, 'main/teacher_create.html')

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
        mongolian_name = request.POST.get('mongolian_name', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        role = request.POST.get('role', '')
        birth_date = request.POST.get('birth_date', '').strip()
        gender = request.POST.get('gender', '').strip()
        city = request.POST.get('city', '').strip()
        district = request.POST.get('district', '').strip()
        notes = request.POST.get('notes', '').strip()
        photo = request.FILES.get('photo')
        
        # Validation
        if not mongolian_name:
            messages.error(request, 'Нэр оруулна уу.')
            return render(request, 'main/teacher_update.html', {'teacher': teacher_profile})
        
        if not phone:
            messages.error(request, 'Утасны дугаар оруулна уу.')
            return render(request, 'main/teacher_update.html', {'teacher': teacher_profile})
        
        if not role or role not in ['TEACHER_BEGINNER', 'TEACHER_INTERMEDIATE', 'TEACHER_ADVANCED']:
            messages.error(request, 'Багшийн түвшин сонгоно уу.')
            return render(request, 'main/teacher_update.html', {'teacher': teacher_profile})
        
        # Утасны дугаар цэвэрлэх
        phone_clean = phone.replace(' ', '').replace('-', '').replace('+976', '')
        
        # Утасны дугаарын формат шалгах
        if not re.match(r'^\d{8}$', phone_clean):
            messages.error(request, 'Утасны дугаар 8 оронтой тоо байх ёстой. Жишээ: 99001234')
            return render(request, 'main/teacher_update.html', {'teacher': teacher_profile})
        
        # Утас давхцаж байгаа эсэх шалгах (өөр хэрэглэгчтэй)
        if UserProfile.objects.filter(phone=phone_clean).exclude(id=teacher_id).exists():
            messages.error(request, f'Утасны дугаар {phone_clean} аль хэдийн бүртгэгдсэн байна.')
            return render(request, 'main/teacher_update.html', {'teacher': teacher_profile})
        
        # Имэйл давхцаж байгаа эсэх шалгах (өөр хэрэглэгчтэй)
        if email and User.objects.filter(email=email).exclude(id=teacher_profile.user.id).exists():
            messages.error(request, f'Имэйл хаяг {email} аль хэдийн бүртгэгдсэн байна.')
            return render(request, 'main/teacher_update.html', {'teacher': teacher_profile})
        
        try:
            # User мэдээлэл шинэчлэх
            user = teacher_profile.user
            name_parts = mongolian_name.split()
            if name_parts:
                user.first_name = name_parts[0]
                if len(name_parts) > 1:
                    user.last_name = ' '.join(name_parts[1:])
                else:
                    user.last_name = ''
            user.email = email if email else ''
            user.save()
            
            # UserProfile шинэчлэх
            teacher_profile.mongolian_name = mongolian_name
            teacher_profile.phone = phone_clean
            teacher_profile.role = role
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
            
            messages.success(request, f'✓ Багш "{mongolian_name}" амжилттай шинэчлэгдлээ!')
            return redirect('main:teacher_list')
            
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
            return render(request, 'main/teacher_update.html', {'teacher': teacher_profile})
    
    return render(request, 'main/teacher_update.html', {'teacher': teacher_profile})

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
def attendance_list(request):
    """Ирц бүртгэх - Багш болон админд харагдана"""
    profile = request.user.profile
    
    # Багш болон админ эрх шалгах
    if not (profile.is_admin or profile.is_teacher):
        messages.error(request, 'Танд ирц бүртгэх эрх байхгүй байна.')
        return redirect('main:dashboard')
    
    # Багш бол өөрийн хичээлүүд, админ бол бүх хичээлүүд
    if profile.is_teacher:
        courses = Course.objects.filter(teacher=profile, is_active=True)
    else:
        courses = Course.objects.filter(is_active=True)
    
    return render(request, 'main/attendance_list.html', {'courses': courses})


@login_required
def attendance_sheet(request, course_id):
    """Ирцийн хуудас - Мөрөөр сурагч, баганаар огноо"""
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    profile = request.user.profile
    
    # Эрх шалгах
    if not (profile.is_admin or profile.is_teacher):
        messages.error(request, 'Танд ирц бүртгэх эрх байхгүй байна.')
        return redirect('main:dashboard')
    
    # Хичээл авах
    course = get_object_or_404(Course, id=course_id, is_active=True)
    
    # Багш бол зөвхөн өөрийн хичээлийн ирц бүртгэнэ
    if profile.is_teacher and course.teacher != profile:
        messages.error(request, 'Та зөвхөн өөрийн хичээлийн ирц бүртгэх эрхтэй.')
        return redirect('main:attendance_list')
    
    # Идэвхтэй бүртгэлтэй сурагчид
    enrollments = Enrollment.objects.filter(
        course=course,
        is_active=True,
        status__in=['APPROVED', 'PENDING']
    ).select_related('student__user').order_by('student__mongolian_name')
    
    if request.method == 'POST':
        # Ирц хадгалах
        saved_count = 0
        
        for enrollment in enrollments:
            for key, value in request.POST.items():
                if key.startswith(f'attendance_{enrollment.id}_'):
                    date_str = key.replace(f'attendance_{enrollment.id}_', '')
                    try:
                        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        
                        # Attendance үүсгэх эсвэл шинэчлэх
                        Attendance.objects.update_or_create(
                            enrollment=enrollment,
                            date=attendance_date,
                            defaults={
                                'present': True,  # Checkbox чагтласан бол ирсэн
                                'notes': ''
                            }
                        )
                        saved_count += 1
                    except ValueError:
                        pass
        
        # Чагтлаагүй checkbox-уудыг тасалсан болгох
        # Бүх огноог авах
        all_dates = set()
        for key in request.POST.keys():
            if key.startswith('attendance_'):
                parts = key.split('_')
                if len(parts) >= 3:
                    date_str = '_'.join(parts[2:])
                    try:
                        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        all_dates.add(attendance_date)
                    except:
                        pass
        
        # Чагтлаагүй бүртгэлүүдийг тасалсан болгох
        for enrollment in enrollments:
            for date in all_dates:
                checkbox_name = f'attendance_{enrollment.id}_{date.strftime("%Y-%m-%d")}'
                if checkbox_name not in request.POST:
                    # Checkbox чагтлаагүй бол тасалсан
                    Attendance.objects.update_or_create(
                        enrollment=enrollment,
                        date=date,
                        defaults={
                            'present': False,
                            'notes': ''
                        }
                    )
        
        messages.success(request, f'✓ Ирц амжилттай хадгалагдлаа!')
        return redirect('main:attendance_sheet', course_id=course_id)
    
    # GET хүсэлт
    # Он/сар шүүлт авах
    from datetime import datetime
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    today = timezone.now().date()
    
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
    
    # Огнооны жагсаалт үүсгэх - хадгалагдсан болон шүүлтийн огноог нэгтгэх
    from collections import defaultdict
    dates_by_month = defaultdict(list)
    
    # 1. Шүүлтийн хугацааны огноо нэмэх
    current_date = start
    while current_date <= end:
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
    
    # Эрх шалгах
    if not (profile.is_admin or profile.is_teacher):
        messages.error(request, 'Танд ирц бүртгэх эрх байхгүй байна.')
        return redirect('main:dashboard')
    
    # Хичээл авах
    course = get_object_or_404(Course, id=course_id, is_active=True)
    
    # Багш бол зөвхөн өөрийн хичээлийн ирц бүртгэнэ
    if profile.is_teacher and course.teacher != profile:
        messages.error(request, 'Та зөвхөн өөрийн хичээлийн ирц бүртгэх эрхтэй.')
        return redirect('main:attendance_list')
    
    # Идэвхтэй бүртгэлтэй сурагчид
    enrollments = Enrollment.objects.filter(
        course=course, 
        is_active=True,
        status__in=['APPROVED', 'PENDING']
    ).select_related('student__user')
    
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
            
            # Ирц бүртгэх
            marked_count = 0
            for enrollment in enrollments:
                is_present = request.POST.get(f'present_{enrollment.id}') == 'on'
                notes = request.POST.get(f'notes_{enrollment.id}', '').strip()
                
                # Ирц үүсгэх эсвэл шинэчлэх
                attendance, created = Attendance.objects.update_or_create(
                    enrollment=enrollment,
                    date=attendance_date,
                    defaults={
                        'present': is_present,
                        'notes': notes
                    }
                )
                marked_count += 1
            
            messages.success(request, f'✓ {attendance_date} өдрийн {marked_count} сурагчийн ирц амжилттай бүртгэгдлээ!')
            return redirect('main:attendance_mark', course_id=course.id)
            
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
    
    # Хамгийн сүүлийн ирцийг харуулах (default огноо болгох)
    from datetime import date
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
            attendance_data.append({
                'enrollment': enrollment,
                'present': True,  # Default ирсэн
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
        
        # Validation
        if not name:
            messages.error(request, 'Хичээлийн нэр оруулна уу.')
            teachers = UserProfile.objects.filter(
                role__in=[UserRole.TEACHER_BEGINNER, UserRole.TEACHER_INTERMEDIATE, UserRole.TEACHER_ADVANCED]
            ).select_related('user')
            return render(request, 'main/course_form.html', {'teachers': teachers})
        
        if not level:
            messages.error(request, 'Түвшин сонгоно уу.')
            teachers = UserProfile.objects.filter(
                role__in=[UserRole.TEACHER_BEGINNER, UserRole.TEACHER_INTERMEDIATE, UserRole.TEACHER_ADVANCED]
            ).select_related('user')
            return render(request, 'main/course_form.html', {'teachers': teachers})
        
        try:
            teacher = UserProfile.objects.get(id=teacher_id) if teacher_id else None
            
            course = Course.objects.create(
                name=name,
                level=level,
                teacher=teacher,
                is_active=is_active
            )
            
            messages.success(request, f'✓ "{name}" сургалт амжилттай үүслээ!')
            return redirect('main:course_list')
        except Exception as e:
            messages.error(request, f'Алдаа гарлаа: {str(e)}')
            teachers = UserProfile.objects.filter(
                role__in=[UserRole.TEACHER_BEGINNER, UserRole.TEACHER_INTERMEDIATE, UserRole.TEACHER_ADVANCED]
            ).select_related('user')
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
        course.is_active = request.POST.get('is_active') == 'on'
        
        teacher_id = request.POST.get('teacher')
        course.teacher = UserProfile.objects.get(id=teacher_id) if teacher_id else None
        
        course.save()
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
def inventory_list(request):
    """Бараа материалын жагсаалт"""
    profile = request.user.profile
    
    # Зөвхөн менежер, нягтлан, админ нар харна
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
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
    
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:inventory_list')
    
    if request.method == 'POST':
        try:
            product = Product(
                code=request.POST.get('code'),
                name=request.POST.get('name'),
                category_id=request.POST.get('category') if request.POST.get('category') else None,
                description=request.POST.get('description', ''),
                purchase_price=Decimal(request.POST.get('purchase_price', 0)),
                selling_price=Decimal(request.POST.get('selling_price', 0)),
                unit=request.POST.get('unit', 'PIECE'),
                current_stock=int(request.POST.get('current_stock', 0)),
                min_stock=int(request.POST.get('min_stock', 0)),
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
    context = {
        'categories': categories,
        'units': Product.UNIT_CHOICES,
    }
    return render(request, 'main/product_form.html', context)


@login_required
def product_edit(request, product_id):
    """Бараа материал засах"""
    profile = request.user.profile
    
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:inventory_list')
    
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        try:
            product.code = request.POST.get('code')
            product.name = request.POST.get('name')
            product.category_id = request.POST.get('category') if request.POST.get('category') else None
            product.description = request.POST.get('description', '')
            product.purchase_price = Decimal(request.POST.get('purchase_price', 0))
            product.selling_price = Decimal(request.POST.get('selling_price', 0))
            product.unit = request.POST.get('unit', 'PIECE')
            product.min_stock = int(request.POST.get('min_stock', 0))
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
    context = {
        'product': product,
        'categories': categories,
        'units': Product.UNIT_CHOICES,
        'is_edit': True,
    }
    return render(request, 'main/product_form.html', context)


@login_required
def stock_movement_create(request):
    """Агуулахын хөдөлгөөн бүртгэх"""
    profile = request.user.profile
    
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
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
def stock_movement_list(request):
    """Агуулахын хөдөлгөөний жагсаалт"""
    profile = request.user.profile
    
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
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
    
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    # Дансуудын үлдэгдэл
    accounts = Account.objects.filter(is_active=True)
    total_cash = accounts.filter(account_type='CASH').aggregate(Sum('balance'))['balance__sum'] or 0
    total_bank = accounts.filter(account_type='BANK').aggregate(Sum('balance'))['balance__sum'] or 0
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
    
    context = {
        'accounts': accounts,
        'total_cash': total_cash,
        'total_bank': total_bank,
        'total_balance': total_balance,
        'suppliers_debt': suppliers_debt,
        'customers_debt': abs(customers_debt),
        'recent_transactions': recent_transactions,
        'recent_purchases': recent_purchases,
        'recent_sales': recent_sales,
    }
    
    return render(request, 'main/finance_dashboard.html', context)


@login_required
def account_opening_balance(request):
    """Дансны эхний үлдэгдэл оруулах"""
    profile = request.user.profile
    
    # Эрх шалгах - зөвхөн нягтлан бодогч болон админ
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
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
    """Худалдан авалтын жагсаалт"""
    profile = request.user.profile
    
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    purchases = Purchase.objects.select_related('supplier', 'created_by').prefetch_related('items__product')
    
    # Шүүлт
    status = request.GET.get('status', '')
    if status:
        purchases = purchases.filter(status=status)
    
    # Статистик
    total_amount = purchases.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_paid = purchases.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
    total_remaining = total_amount - total_paid
    
    context = {
        'purchases': purchases[:50],  # Сүүлийн 50
        'total_amount': total_amount,
        'total_paid': total_paid,
        'total_remaining': total_remaining,
        'selected_status': status,
        'status_choices': Purchase.STATUS_CHOICES,
    }
    
    return render(request, 'main/purchase_list.html', context)


@login_required
def sale_list(request):
    """Борлуулалтын жагсаалт"""
    profile = request.user.profile
    
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    sales = Sale.objects.select_related('customer', 'created_by').prefetch_related('items__product')
    
    # Шүүлт
    status = request.GET.get('status', '')
    if status:
        sales = sales.filter(status=status)
    
    # Статистик
    total_amount = sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_paid = sales.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
    total_remaining = total_amount - total_paid
    
    context = {
        'sales': sales[:50],  # Сүүлийн 50
        'total_amount': total_amount,
        'total_paid': total_paid,
        'total_remaining': total_remaining,
        'selected_status': status,
        'status_choices': Sale.STATUS_CHOICES,
    }
    
    return render(request, 'main/sale_list.html', context)


@login_required
def transaction_list(request):
    """Гүйлгээний жагсаалт"""
    profile = request.user.profile
    
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
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
    
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
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
    
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
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
    # Admin эрх шалгах
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(
            request, 
            'Ерөнхий журнал харах эрх танд байхгүй. '
            'Зөвхөн админ хэрэглэгч харах боломжтой.'
        )
        return redirect('main:finance_dashboard')
    
    entries = AccountingEntry.objects.select_related(
        'debit_account', 'credit_account', 'created_by'
    ).order_by('-entry_date', '-entry_number')
    
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
    
    # Статистик
    total_entries = entries.count()
    total_debit = entries.aggregate(Sum('debit_amount'))['debit_amount__sum'] or 0
    total_credit = entries.aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0
    
    context = {
        'entries': entries,
        'total_entries': total_entries,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'main/journal_list.html', context)


@login_required
def journal_create(request):
    """Шинэ журналын бичилт үүсгэх"""
    # Admin эрх шалгах
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(
            request, 
            'Журналын бичилт үүсгэх эрх танд байхгүй. '
            'Зөвхөн админ хэрэглэгч үүсгэх боломжтой.'
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
    # Admin эрх шалгах
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Журналын бичилт устгах эрх танд байхгүй.')
        return redirect('main:journal_list')
    
    entry = get_object_or_404(AccountingEntry, id=entry_id)


@login_required
def journal_delete(request, entry_id):
    """Журналын бичилт устгах"""
    entry = get_object_or_404(AccountingEntry, id=entry_id)
    
    if request.method == 'POST':
        entry_number = entry.entry_number
        entry.delete()
        messages.success(request, f'Журналын бичилт {entry_number} устгагдлаа.')
        return redirect('main:journal_list')
    
    return redirect('main:journal_list')


@login_required
def chart_of_accounts_list(request):
    """Дансны төлөвлөгөө харах"""
    # Admin эрх шалгах
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(
            request, 
            'Дансны төлөвлөгөө харах эрх танд байхгүй. '
            'Зөвхөн админ хэрэглэгч (is_staff эсвэл superuser) харах боломжтой.'
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
    
    # Эрх шалгах (админ эсвэл нягтлан бодогч)
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    # Зөвхөн банкны гүйлгээ (кассын гүйлгээ биш)
    transactions = BankTransaction.objects.filter(
        account_type='BANK'
    ).select_related(
        'bank_account', 'offset_account'
    ).prefetch_related(
        'allocations__student', 'allocations__course'
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
        from django.db.models import Q
        # Бүх хувилбараар хайх
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
    
    # Статистик тооцоолох
    total_count = transactions.count()
    unprocessed_count = transactions.filter(is_processed=False).count()
    processed_count = transactions.filter(is_processed=True).count()
    
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
    
    context = {
        'transactions': page_obj,
        'bank_accounts': bank_accounts,
        'all_accounts': all_accounts,
        'total_count': total_count,
        'unprocessed_count': unprocessed_count,
        'processed_count': processed_count,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        # Филтерийн утгууд (form-д харуулах)
        'selected_bank_account': bank_account_id,
        'selected_offset_account': offset_account_id,
        'search_description': search_description,
        'selected_is_processed': is_processed,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'main/bank_transaction_list.html', context)


@login_required
def link_bank_transaction_to_journal(request, transaction_id):
    """Банк/кассын гүйлгээнд эсрэг данс холбох, орлого ангилах, журналын бичилт үүсгэх"""
    profile = request.user.profile
    
    # Эрх шалгах
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
        messages.error(request, 'Энэ үйлдэл хийх эрх танд байхгүй.')
        return redirect('main:bank_transaction_list')
    
    # Гүйлгээ авах (банк болон кассын гүйлгээ хоёуланд зориулна)
    transaction = get_object_or_404(BankTransaction, id=transaction_id)
    
    if request.method == 'POST':
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
                income_type = request.POST.get('income_type')
                if income_type:
                    transaction.income_type = income_type
                    
                    # Сурагчийн төлбөр бол - олон хуваарилалт хадгална
                    if income_type == 'STUDENT_PAYMENT':
                        # Хуучин хуваарилалтуудыг устгах
                        PaymentAllocation.objects.filter(transaction=transaction).delete()
                        
                        # Шинэ хуваарилалтуудыг үүсгэх
                        allocations_saved = 0
                        total_allocated = Decimal(0)
                        
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
                                        alloc = PaymentAllocation.objects.create(
                                            transaction=transaction,
                                            student_id=student_id,
                                            course_id=course_id,
                                            month=int(month_str),
                                            year=int(year_str),
                                            amount=Decimal(amount)
                                        )
                                        allocations_saved += 1
                                        total_allocated += Decimal(amount)
                                    except Exception as e:
                                        print(f"Allocation save error: {e}")
                                        import traceback
                                        traceback.print_exc()
                        
                        # Хуучин fields-үүдийг цэвэрлэх
                        transaction.income_student = None
                        transaction.income_course = None
                        transaction.income_month = None
                        transaction.income_year = None
                        transaction.income_sale = None
                        
                        if allocations_saved == 0:
                            messages.warning(request, 'Төлбөрийн хуваарилалт хадгалагдсангүй.')
                        else:
                            # Нийт дүн шалгах
                            if total_allocated != transaction.income_amount:
                                messages.warning(
                                    request,
                                    f'Анхааруулга: Хуваарилалтын нийт дүн ({total_allocated:,.0f}₮) '
                                    f'гүйлгээний дүнтэй ({transaction.income_amount:,.0f}₮) таарахгүй байна.'
                                )
                    
                    # Барааны борлуулалт бол
                    elif income_type == 'PRODUCT_SALE':
                        sale_id = request.POST.get('sale')
                        if sale_id:
                            transaction.income_sale_id = sale_id
                        transaction.income_student = None
                        transaction.income_course = None
                        transaction.income_month = None
                    
                    # Бусад төрөл
                    else:
                        transaction.income_student = None
                        transaction.income_course = None
                        transaction.income_month = None
                        transaction.income_sale = None
            
            transaction.save()
            
            # Журналын бичилт үүсгэх
            from .import_bank_transactions import regenerate_accounting_entries
            
            # Энэ нэг гүйлгээний журнал үүсгэх
            result = regenerate_accounting_entries([transaction], request.user)
            
            if result > 0:
                messages.success(
                    request, 
                    f'✓ Эсрэг данс "{offset_account.code} - {offset_account.name}" холбогдож, '
                    f'журналын бичилт үүслээ!'
                )
                # Банк эсвэл кассын жагсаалт руу буцах
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
    students = UserProfile.objects.filter(role=UserRole.STUDENT).order_by('mongolian_name')
    sales = Sale.objects.filter(status__in=['COMPLETED', 'PAID']).order_by('-sale_date')[:50]
    courses = Course.objects.filter(is_active=True).order_by('level', 'name')
    months = [(i, f'{i}-р сар') for i in range(1, 13)]
    
    # Одоо байгаа хуваарилалтууд
    existing_allocations = transaction.allocations.all().select_related('student', 'course')
    
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
        'income_types': BankTransaction.INCOME_TYPE_CHOICES,
        'cash_flow_indicators': cash_flow_indicators,
        'existing_allocations': existing_allocations,
    }
    
    return render(request, 'main/link_bank_transaction.html', context)


@login_required
def classify_income(request, transaction_id):
    """Банкны гүйлгээний орлогыг ангилах - төрөл, сурагч, бараа (олон хуваарилалт дэмжинэ)"""
    from datetime import datetime
    profile = request.user.profile
    
    # Эрх шалгах
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
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
    students = UserProfile.objects.filter(role=UserRole.STUDENT).order_by('mongolian_name')
    sales = Sale.objects.filter(status__in=['COMPLETED', 'PAID']).order_by('-sale_date')[:50]  # Сүүлийн 50 борлуулалт
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
    
    # Эрх шалгах (админ эсвэл нягтлан бодогч)
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
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
    students = UserProfile.objects.filter(role=UserRole.STUDENT).order_by('mongolian_name')
    
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
    
    # Эрх шалгах
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    # Зөвхөн кассын гүйлгээ
    transactions = BankTransaction.objects.filter(
        account_type='CASH'
    ).select_related(
        'bank_account', 'offset_account'
    ).prefetch_related(
        'allocations__student', 'allocations__course'
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
    }
    
    return render(request, 'main/cash_transaction_list.html', context)


@login_required
def cash_transaction_edit(request, transaction_id):
    """Кассын гүйлгээ засах"""
    profile = request.user.profile
    
    # Эрх шалгах
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    # Гүйлгээг авах
    transaction = get_object_or_404(BankTransaction, id=transaction_id, account_type='CASH')
    
    # Одоо байгаа хуваарилалтууд
    existing_allocations = PaymentAllocation.objects.filter(transaction=transaction).select_related('student', 'course')
    
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
    students = UserProfile.objects.filter(role=UserRole.STUDENT).order_by('mongolian_name')
    
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
    
    # Эрх шалгах
    if not (profile.role in [UserRole.MANAGER, UserRole.ACCOUNTANT] or profile.is_admin or request.user.is_superuser):
        messages.error(request, 'Энэ үйлдэл хийх эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    # Гүйлгээг авах
    transaction = get_object_or_404(BankTransaction, id=transaction_id, account_type='CASH')
    
    if request.method == 'POST':
        try:
            # Журналыг устгах (байвал)
            if transaction.accounting_entry:
                transaction.accounting_entry.delete()
            
            # Хуваарилалтууд автоматаар устана (CASCADE)
            transaction.delete()
            
            messages.success(request, 'Кассын гүйлгээ амжилттай устгагдлаа.')
            return redirect('main:cash_transaction_list')
            
        except Exception as e:
            messages.error(request, f'Устгахад алдаа гарлаа: {str(e)}')
            return redirect('main:cash_transaction_list')
    
    # GET request - баталгаажуулах хуудас харуулах
    return render(request, 'main/cash_transaction_delete.html', {'transaction': transaction})
