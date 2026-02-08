# Готопа бясалгалын төв - Хэрэглэгчийн удирдлага

## Систем тохируулсан!

### Хэрэглэгчийн эрхийн түвшин

Систем дараах 7 төрлийн эрхийг дэмжинэ:

1. **Тэргүүн** (PRESIDENT) - Хамгийн өндөр эрх
2. **Захирал** (DIRECTOR) - Удирдлагын эрх
3. **Менежер** (MANAGER) - Менежментийн эрх
4. **Анхан шатны багш** (TEACHER_BEGINNER)
5. **Дунд шатны багш** (TEACHER_INTERMEDIATE)
6. **Дээд шатны багш** (TEACHER_ADVANCED)
7. **Сурагч** (STUDENT) - Үндсэн хэрэглэгч

### Database Models

#### 1. UserProfile
Хэрэглэгчийн дэлгэрэнгүй мэдээлэл:
- Эрх (Role)
- Монгол нэр
- Утас, имэйл
- Төрсөн өдөр, хүйс
- Хаяг (хот, дүүрэг)
- Зураг
- Тэмдэглэл

#### 2. Course (Сургалт)
- Нэр, түвшин (Анхан/Дунд/Дээд/VIP)
- Багш
- Эхлэх/Дуусах огноо
- Үнэ, үргэлжлэх хугацаа
- Дээд хязгаар

#### 3. Enrollment (Бүртгэл)
- Сурагч + Сургалт
- Төлөв (Хүлээгдэж буй/Баталсан/Төгссөн/Цуцалсан)
- Төлбөр (дүн, огноо)
- Гэрчилгээ

#### 4. Attendance (Ирц)
- Бүртгэл + Огноо
- Ирсэн эсэх
- Тэмдэглэл

## Ашиглах заавар

### 1. Admin панель нэвтрэх

```bash
# Superuser үүсгэх (хэрэв байхгүй бол)
python manage.py createsuperuser

# Server ажиллуулах
python manage.py runserver

# Browser-д нээх
http://127.0.0.1:8000/admin
```

### 2. Жишээ хэрэглэгчид үүсгэх

```bash
python manage.py shell
```

Дараа нь Python shell дотор:

```python
from main.import_excel import create_sample_users

# Жишээ хэрэглэгчид үүсгэх
create_sample_users()

# Үүссэн хэрэглэгчид:
# - president (Тэргүүн)
# - director (Захирал)
# - teacher_beginner (Анхан шатны багш)
# - teacher_intermediate (Дунд шатны багш)
# - teacher_advanced (Дээд шатны багш)
```

Нууц үг тохируулах:
```bash
python manage.py changepassword president
python manage.py changepassword director
# ... гэх мэт
```

### 3. Excel-с сурагчдын мэдээлэл импортлох

**Урьдчилсан шаардлага:**
- Excel файл дээр дараах баганууд байх ёстой:
  - `Нэр` - Сурагчийн нэр
  - `Утас` - Утасны дугаар (заавал биш)
  - `Хаяг` - Хаяг (заавал биш)

**Import хийх:**

```bash
python manage.py shell
```

Python shell дотор:

```python
from main.import_excel import import_students

# Excel файлаас импортлох
import_students('Бясалгагчийн_мэдээллийн_бааз.xlsx')

# Эсвэл бүрэн path оруулах
import_students(r'D:\Bayar\programming\python\gotopa\Бясалгагчийн_мэдээллийн_бааз.xlsx')
```

**Анхаарах:**
- Excel файлын баганын нэрс таны файлын дагуу өөрчлөгдөж болно
- `main/import_excel.py` файл дээр `import_students()` функц дотор баганын нэрсийг засч тохируулаарай

### 4. Admin панелийн боломжууд

**Хэрэглэгчид (Users):**
- Шинэ хэрэглэгч нэмэх
- Эрх өөрчлөх (Тэргүүн, Захирал, Багш, Сурагч гэх мэт)
- Хувийн мэдээлэл засах

**Сургалт (Courses):**
- Шинэ сургалт нэмэх
- Багш томилох
- Элссэн сурагчдын тоо харах

**Бүртгэл (Enrollments):**
- Сурагчдыг сургалтад бүртгэх
- Төлбөр тэмдэглэх (bulk action)
- Баталгаажуулах
- Гэрчилгээ олгох

**Ирц (Attendance):**
- Өдөр тутмын ирц бүртгэх
- Сургалтаар шүүх
- Тайлан гаргах

## Дараагийн алхамууд

### 1. Excel баганын нэрс тохируулах

[main/import_excel.py](main/import_excel.py) файл дээр 28-30 мөрнүүдийг өөрийн Excel файлын баганын нэртэй тааруулах:

```python
# Өөрийн Excel-ийн баганын нэрээр солих
name = str(row.get('Овог Нэр', '')).strip()  # Эсвэл 'Нэр Овог', 'ФИО' гэх мэт
phone = str(row.get('Утасны дугаар', '')).strip()  # Эсвэл 'Холбоо барих', 'Утас' гэх мэт
address = str(row.get('Гэрийн хаяг', '')).strip()  # Эсвэл 'Хаяг', 'Оршин суугаа газар' гэх мэт
```

### 2. Нэмэлт талбар нэмэх

Хэрэв Excel дээр нэмэлт мэдээлэл байвал (жишээ нь: Төрсөн өдөр, Хүйс, Имэйл гэх мэт), `UserProfile` model болон import script дээр нэмж болно.

### 3. Permissions тохируулах

Django-ийн permission system ашиглаж эрх тохируулах боломжтой:

```python
# views.py дээр
from django.contrib.auth.decorators import login_required, permission_required

@login_required
def student_list(request):
    # Зөвхөн нэвтэрсэн хэрэглэгч үзнэ
    if request.user.profile.is_teacher or request.user.profile.is_admin:
        # Багш болон админ хандана
        students = UserProfile.objects.filter(role=UserRole.STUDENT)
        return render(request, 'students.html', {'students': students})
    else:
        return HttpResponseForbidden("Хандах эрхгүй")
```

## Файлын бүтэц

```
gotopa/
├── main/
│   ├── models.py           # UserProfile, Course, Enrollment, Attendance
│   ├── admin.py            # Admin панелийн тохиргоо
│   ├── import_excel.py     # Excel импорт script
│   └── migrations/         # Database migrations
├── Бясалгагчийн_мэдээллийн_бааз.xlsx  # Сурагчдын Excel файл
└── manage.py
```

## Түгээмэл асуултууд

**Q: Excel файл импортлохдоо алдаа гарвал?**
A: 
1. Баганын нэрс зөв эсэхийг шалгах
2. Excel файл хаалттай эсэхийг шалгах
3. `import_excel.py` дээр баганын нэрсийг засах

**Q: Хэрэглэгчийн нууц үг яаж солих вэ?**
A: `python manage.py changepassword <username>`

**Q: Сурагчийн эрхийг багш болгох гэвэл?**
A: Admin панель дээр User-г нээж, Profile дээр Role-г солих

**Q: Нэг сурагч хэд хэдэн сургалтад элсэх боломжтой юу?**
A: Тийм, Enrollment model олон сургалтад бүртгүүлэх боломжтой

---

**Анхааруулга:** Production орчинд ашиглахаасаа өмнө:
1. SECRET_KEY өөрчилөх
2. DEBUG = False болгох
3. ALLOWED_HOSTS тохируулах
4. PostgreSQL database ашиглах
5. Static/Media файлуудыг зөв хостлох
