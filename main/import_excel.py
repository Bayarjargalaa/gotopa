"""
Excel файлаас хэрэглэгч, сурагчдын мэдээллийг Django database-руу импортлох script

Ашиглах заавар:
python manage.py shell
>>> from main.import_excel import import_students
>>> import_students('Бясалгагчийн_мэдээллийн_бааз.xlsx')
"""

import os
import sys
import django

# Django environment тохируулах (шууд python-оор ажиллуулахад)
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    # Script-ийн байршлаас project root-ийг олох
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # main/ -> gotopa/
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
    django.setup()

import pandas as pd
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from django.utils.text import slugify
from main.models import Course, Enrollment, UserProfile, UserRole

def import_students(excel_file):
    """
    Excel файлаас сурагчдын мэдээллийг импортлох
    
    Parameters:
    excel_file (str): Excel файлын нэр эсвэл path
    """
    try:
        # Excel файл уншиж
        df = pd.read_excel(excel_file, engine='openpyxl')
        
        print(f"Нийт мөр: {len(df)}")
        print(f"Баганууд: {list(df.columns)}")
        
        created_count = 0
        updated_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                # Excel-ээс мэдээлэл авах (баганын нэрсийг таны Excel файлын дагуу өөрчилнө үү)
                # Жишээ нь:
                name = str(row.get('Нэр', '')).strip() if pd.notna(row.get('Нэр')) else ''
                phone = str(row.get('Утас', '')).strip().replace(' ', '').replace('-', '') if pd.notna(row.get('Утас')) else ''
                address = str(row.get('Хаяг', '')).strip() if pd.notna(row.get('Хаяг')) else ''
                email = str(row.get('Имэйл', '')).strip() if pd.notna(row.get('Имэйл')) else ''
                
                if not name:
                    print(f"Мөр {index + 2}: Нэр хоосон байна, алгасав.")
                    error_count += 1
                    continue
                
                # Username үүсгэх (утасны дугаараас)
                if phone and len(phone) >= 8:
                    username = f"student_{phone[-8:]}"
                else:
                    username = name.replace(' ', '_').lower()
                
                # User үүсгэх эсвэл олох
                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'first_name': name.split()[0] if name else '',
                        'last_name': ' '.join(name.split()[1:]) if len(name.split()) > 1 else '',
                        'email': email if email and '@' in email else '',
                    }
                )
                
                # Имэйл шинэчлэх (хэрэв шинэ имэйл байвал)
                if not user_created and email and '@' in email and not user.email:
                    user.email = email
                    user.save()
                
                # UserProfile үүсгэх эсвэл шинэчлэх
                profile, profile_created = UserProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        'role': UserRole.STUDENT,
                        'mongolian_name': name,
                        'phone': phone,
                        'address': address,
                        'is_active_student': True,
                    }
                )
                
                if profile_created:
                    created_count += 1
                    # Анхны нууц үг: утасны сүүлийн 8 орон
                    if phone and len(phone) >= 8:
                        user.set_password(phone[-8:])
                        user.save()
                        print(f"✓ Шинээр үүсгэсэн: {name} (Утас: {phone[-8:]}, Нууц үг: {phone[-8:]})")
                    else:
                        print(f"✓ Шинээр үүсгэсэн: {name} (Нууц үг тохируулаагүй)")
                else:
                    updated_count += 1
                    print(f"↻ Шинэчилсэн: {name}")
                    
            except Exception as e:
                error_count += 1
                print(f"✗ Алдаа мөр {index + 2}: {str(e)}")
                continue
        print(f"\n💡 Сурагч нар дараахаар нэвтэрч болно:")
        print(f"   - Утасны дугаараар (сүүлийн 8 орон)")
        print(f"   - Имэйл хаягаар (хэрэв бүртгэсэн бол)")
        print(f"   - Username-ээр (student_XXXXXXXX)")
        
        print(f"\n=== Дүн ===")
        print(f"Шинээр үүсгэсэн: {created_count}")
        print(f"Шинэчилсэн: {updated_count}")
        print(f"Алдаа: {error_count}")
        print(f"Нийт: {created_count + updated_count + error_count}")
        
        return {
            'created': created_count,
            'updated': updated_count,
            'errors': error_count
        }
        
    except FileNotFoundError:
        print(f"Файл олдсонгүй: {excel_file}")
        print("Одоогийн directory-д байгаа файлууд:")
        import os
        for f in os.listdir('.'):
            if f.endswith('.xlsx'):
                print(f"  - {f}")
        return None


def import_gotopa_names(excel_file):
    """`Нэрс готопа.xlsx` бүтэцтэй файлаас сурагч, сургалтын мэдээлэл импортлох."""

    course_level_map = {
        'анхан шат 1': 'BEGINNER_1',
        'анхан 1': 'BEGINNER_1',
        'анхан шат 2': 'BEGINNER_2',
        'анхан 2': 'BEGINNER_2',
        'дунд': 'INTERMEDIATE',
        'ахисан': 'ADVANCED',
        'ахисан шат': 'ADVANCED',
    }

    def clean_phone(value):
        if pd.isna(value):
            return ''
        digits_only = ''.join(ch for ch in str(value) if ch.isdigit())
        return digits_only[-8:] if len(digits_only) >= 8 else ''

    def parse_name(raw_name):
        name = str(raw_name).strip() if pd.notna(raw_name) else ''
        if not name:
            return '', '', ''

        if '.' in name:
            surname_part, given_name = name.split('.', 1)
            last_name = surname_part.strip()[:1]
            first_name = given_name.strip()
        else:
            parts = name.split()
            last_name = parts[0][:1] if len(parts) > 1 else ''
            first_name = ' '.join(parts[1:]).strip() if len(parts) > 1 else name

        return last_name, first_name, name

    def build_username(phone, full_name, row_number):
        if phone:
            return f"student_{phone}"

        base = slugify(full_name, allow_unicode=True).replace('-', '_') or f"student_import_{row_number}"
        username = f"student_{base}"
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix += 1
            username = f"student_{base}_{suffix}"
        return username

    def find_profile(phone, last_name, first_name, full_name):
        if phone:
            profile = UserProfile.objects.select_related('user').filter(role=UserRole.STUDENT, phone=phone).first()
            if profile:
                return profile

        profile = UserProfile.objects.select_related('user').filter(
            role=UserRole.STUDENT,
            first_name=first_name,
            last_name=last_name,
        ).first()
        if profile:
            return profile

        return UserProfile.objects.select_related('user').filter(
            role=UserRole.STUDENT,
            mongolian_name=full_name,
        ).first()

    def resolve_course(course_name):
        normalized = str(course_name).strip().lower()
        level = course_level_map.get(normalized)
        if level:
            return Course.objects.filter(level=level, is_active=True).order_by('-start_date', '-id').first()

        return Course.objects.filter(name=str(course_name).strip(), is_active=True).order_by('-start_date', '-id').first()

    try:
        df = pd.read_excel(excel_file, engine='openpyxl')

        print(f"Нийт мөр: {len(df)}")
        print(f"Баганууд: {list(df.columns)}")

        created_students = 0
        updated_students = 0
        created_enrollments = 0
        skipped_rows = 0
        error_count = 0

        for index, row in df.iterrows():
            row_number = index + 2
            try:
                raw_name = row.get('Нэрс', '')
                raw_phone = row.get('Утас', '')
                raw_course = row.get('Анги', '')

                last_name, first_name, full_name = parse_name(raw_name)
                phone = clean_phone(raw_phone)
                course_name = str(raw_course).strip() if pd.notna(raw_course) else ''

                if not first_name:
                    skipped_rows += 1
                    print(f"Мөр {row_number}: Нэр хоосон тул алгасав.")
                    continue

                if not course_name:
                    skipped_rows += 1
                    print(f"Мөр {row_number}: Хичээлийн нэр хоосон тул алгасав.")
                    continue

                course = resolve_course(course_name)
                if not course:
                    error_count += 1
                    print(f"✗ Мөр {row_number}: '{course_name}' сургалт олдсонгүй.")
                    continue

                with transaction.atomic():
                    profile = find_profile(phone, last_name, first_name, full_name)

                    if profile:
                        user = profile.user
                        updated_students += 1
                    else:
                        username = build_username(phone, full_name, row_number)
                        user = User.objects.create(username=username)
                        profile = UserProfile.objects.create(user=user, role=UserRole.STUDENT)
                        created_students += 1

                    user.first_name = first_name
                    user.last_name = last_name
                    user.save()

                    profile.role = UserRole.STUDENT
                    profile.last_name = last_name
                    profile.first_name = first_name
                    profile.mongolian_name = full_name
                    if phone:
                        profile.phone = phone
                    profile.is_active_student = True
                    if not profile.enrollment_date:
                        profile.enrollment_date = timezone.now().date()
                    profile.save()

                    if phone and not user.has_usable_password():
                        user.set_password(phone)
                        user.save()

                    enrollment, enrollment_created = Enrollment.objects.get_or_create(
                        student=profile,
                        course=course,
                        defaults={
                            'status': 'APPROVED',
                            'is_active': True,
                        }
                    )
                    if not enrollment_created:
                        updated_fields = []
                        if enrollment.status != 'APPROVED':
                            enrollment.status = 'APPROVED'
                            updated_fields.append('status')
                        if not enrollment.is_active:
                            enrollment.is_active = True
                            updated_fields.append('is_active')
                        if updated_fields:
                            enrollment.save(update_fields=updated_fields + ['updated_at'])
                    else:
                        created_enrollments += 1

                    print(f"✓ Мөр {row_number}: {full_name} -> {course.name}")

            except Exception as error:
                error_count += 1
                print(f"✗ Мөр {row_number}: {error}")

        print("\n=== Дүн ===")
        print(f"Шинээр үүсгэсэн сурагч: {created_students}")
        print(f"Шинэчилсэн сурагч: {updated_students}")
        print(f"Шинээр үүсгэсэн бүртгэл: {created_enrollments}")
        print(f"Алгассан мөр: {skipped_rows}")
        print(f"Алдаа: {error_count}")

        return {
            'created_students': created_students,
            'updated_students': updated_students,
            'created_enrollments': created_enrollments,
            'skipped_rows': skipped_rows,
            'errors': error_count,
        }

    except FileNotFoundError:
        print(f"Файл олдсонгүй: {excel_file}")
        return None
    except Exception as error:
        print(f"Алдаа гарлаа: {error}")
        import traceback
        traceback.print_exc()
        return None
        
    except Exception as e:
        print(f"Алдаа гарлаа: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def create_sample_users():
    """
    Жишээ хэрэглэгчид үүсгэх
    """
    users_data = [
        {
            'username': 'president',
            'first_name': 'Тэргүүн',
            'last_name': 'Гүрү',
            'email': 'president@gotopa.mn',
            'mongolian_name': 'Гүрү Готопа',
            'phone': '99001234',
            'role': UserRole.PRESIDENT,
            'is_staff': True,
        },
        {
            'username': 'director',
            'first_name': 'Захирал',
            'last_name': 'Доржготов',
            'email': 'director@gotopa.mn',
            'mongolian_name': 'Доржготов',
            'phone': '99001235',
            'role': UserRole.DIRECTOR,
            'is_staff': True,
        },
        {
            'username': 'teacher_beginner',
            'first_name': 'Багш',
            'last_name': 'Анхан',
            'email': 'teacher1@gotopa.mn',
            'mongolian_name': 'Багш Анхан',
            'phone': '99001236',
            'role': UserRole.TEACHER_BEGINNER,
            'is_staff': True,
        },
        {
            'username': 'teacher_intermediate',
            'first_name': 'Багш',
            'last_name': 'Дунд',
            'email': 'teacher2@gotopa.mn',
            'mongolian_name': 'Багш Дунд',
            'phone': '99001237',
            'role': UserRole.TEACHER_INTERMEDIATE,
            'is_staff': True,
        },
        {
            'username': 'teacher_advanced',
            'first_name': 'Багш',
            'last_name': 'Дээд',
            'email': 'teacher3@gotopa.mn',
            'mongolian_name': 'Багш Дээд',
            'phone': '99001238',
            'role': UserRole.TEACHER_ADVANCED,
            'is_staff': True,
        },
    ]
    
    for user_data in users_data:
        # User үүсгэх
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults={
                'first_name': user_data['first_name'],
                'last_name': user_data.get('last_name', ''),
                'email': user_data['email'],
                'is_staff': user_data.get('is_staff', False),
            }
        )
        
        # Имэйл шинэчлэх (хэрэв байхгүй бол)
        if not user.email:
            user.email = user_data['email']
            user.save()
        
        # UserProfile үүсгэх/шинэчлэх
        profile, _ = UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'mongolian_name': user_data['mongolian_name'],
                'phone': user_data['phone'],
                'role': user_data['role'],
            }
        )
    
    print("\n✓ Жишээ хэрэглэгчид амжилттай үүссэн!")
    print("\n📱 Утасаар нэвтрэх:")
    print("  - 99001234 / Тэргүүн")
    print("  - 99001235 / Захирал")
    print("  - 99001236 / Анхан шатны багш")
    print("  - 99001237 / Дунд шатны багш")
    print("  - 99001238 / Дээд шатны багш")
    print("\n📧 Имэйлээр нэвтрэх:")
    print("  - president@gotopa.mn")
    print("  - director@gotopa.mn")
    print("  - teacher1@gotopa.mn")
    print("\n👤 Username-ээр нэвтрэх:")
    print("  - president")
    print("  - director")
    print("  - teacher_beginner")
    print("\n💡 Нууц үг тохируулах: python manage.py changepassword <username>")
    
    # Дунд шатны багш
    user4, _ = User.objects.get_or_create(
        username='teacher_intermediate',
        defaults={'first_name': 'Багш', 'last_name': 'Дунд', 'is_staff': True}
    )
    UserProfile.objects.update_or_create(
        user=user4,
        defaults={
            'role': UserRole.TEACHER_INTERMEDIATE,
            'mongolian_name': 'Багш Дунд',
            'phone': '99223344'
        }
    )
    
    # Дээд шатны багш
    user5, _ = User.objects.get_or_create(
        username='teacher_advanced',
        defaults={'first_name': 'Багш', 'last_name': 'Дээд', 'is_staff': True}
    )
    UserProfile.objects.update_or_create(
        user=user5,
        defaults={
            'role': UserRole.TEACHER_ADVANCED,
            'mongolian_name': 'Багш Дээд',
            'phone': '99334455'
        }
    )
    
    print("✓ Жишээ хэрэглэгчид амжилттай үүссэн!")
    print("  - president / Тэргүүн")
    print("  - director / Захирал")
    print("  - teacher_beginner / Анхан шатны багш")
    print("  - teacher_intermediate / Дунд шатны багш")
    print("  - teacher_advanced / Дээд шатны багш")
    print("\nНууц үг тохируулах: python manage.py changepassword <username>")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
        print(f"Excel файл импортлож байна: {excel_file}")
        import_students(excel_file)
    else:
        print("Ашиглах: python main/import_excel.py <excel_file.xlsx>")
        print("Жишээ:   python main/import_excel.py Бясалгагчийн_мэдээллийн_бааз.xlsx")
