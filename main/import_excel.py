"""
Excel файлаас хэрэглэгч, сурагчдын мэдээллийг Django database-руу импортлох script

Ашиглах заавар:
python manage.py shell
>>> from main.import_excel import import_students
>>> import_students('Бясалгагчийн_мэдээллийн_бааз.xlsx')
"""

import pandas as pd
from django.contrib.auth.models import User
from django.utils import timezone
from main.models import UserProfile, UserRole

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
    print("Энэ script-ийг Django shell дотор ажиллуулна уу:")
    print("python manage.py shell")
    print(">>> from main.import_excel import import_students, create_sample_users")
    print(">>> create_sample_users()  # Жишээ хэрэглэгчид үүсгэх")
    print(">>> import_students('Бясалгагчийн_мэдээллийн_бааз.xlsx')  # Excel импорт")
