# Утас/Имэйлээр нэвтрэх систем

## 🎉 Шинэ боломжууд!

Одоо хэрэглэгч **3 төрлөөр** нэвтэрч болно:

### 1️⃣ Утасны дугаараар
```
99001234    # Тэргүүн
99001235    # Захирал
99001236    # Анхан шатны багш
88001234    # Сурагч (импорт хийсний дараа)
```

### 2️⃣ Имэйл хаягаар
```
president@gotopa.mn
director@gotopa.mn
teacher1@gotopa.mn
student@email.com
```

### 3️⃣ Username-ээр (өмнөх систем)
```
president
director
teacher_beginner
student_88001234
```

---

## 🔧 Техникийн тайлбар

### Authentication Backend

Шинээр үүсгэсэн `main/backends.py`:
- `PhoneOrEmailBackend` класс
- Эхлээд username шалгана
- Дараа нь имэйл шалгана
- Эцэст нь утасны дугаараар шалгана (сүүлийн 8 орон)

### Settings тохиргоо

`AUTHENTICATION_BACKENDS` нэмэгдсэн:
```python
AUTHENTICATION_BACKENDS = [
    'main.backends.PhoneOrEmailBackend',  # Утас/имэйл
    'django.contrib.auth.backends.ModelBackend',  # Username
]
```

### Login форм

- Label: "Утас / Имэйл / Нэвтрэх нэр"
- Placeholder: "88001234 эсвэл name@email.com"
- Тусламжийн текст нэмэгдсэн

---

## 📊 Импорт систем шинэчилгдсэн

### Excel импорт - Шинэ функц

`import_students()` функц одоо:
1. Имэйл багана уншина (`Имэйл`)
2. Утасны форматыг цэвэрлэнэ (зай, зураас арилгана)
3. Username: `student_XXXXXXXX` (сүүлийн 8 орон)
4. Анхны нууц үг: утасны сүүлийн 8 орон
5. User.email field шинэчилнэ

### Жишээ:

Excel файлд:
```
Нэр           | Утас          | Имэйл              | Хаяг
-----------------------------------------------------------------
Бат           | 99-88-12-34   | bat@email.com      | УБ, 1-р хороо
Дорж          | 88 00 12 34   | dorj@email.com     | УБ, 2-р хороо
```

Үүсэх:
```
Username: student_99881234, Password: 99881234
Нэвтрэх: 99881234 / bat@email.com / student_99881234

Username: student_88001234, Password: 88001234
Нэвтрэх: 88001234 / dorj@email.com / student_88001234
```

---

## 🚀 Ашиглах заавар

### 1. Нууц үг тохируулах

**Жишээ хэрэглэгчдэд:**
```bash
python manage.py changepassword president
# Утас: 99001234
# Имэйл: president@gotopa.mn
# Username: president
# 3-аараа нэвтэрч болно (нэг нууц үгээр)
```

### 2. Сурагч импорт хийх

```bash
python manage.py shell
```

```python
from main.import_excel import import_students
import_students('path/to/file.xlsx')
```

Шаардлагатай Excel баганууд:
- `Нэр` - Монгол нэр (заавал)
- `Утас` - Утасны дугаар (заавал, нууц үг болно)
- `Имэйл` - Имэйл хаяг (заавал биш)
- `Хаяг` - Хаяг (заавал биш)

### 3. Нэвтрэх

Login хуудас руу очоод:
- **Утас:** `99001234`
- **Имэйл:** `president@gotopa.mn`
- **Username:** `president`
- **Нууц үг:** (тохируулсан нууц үг)

---

## ✅ Давуу тал

1. **Хялбар санах** - Утасаараа нэвтэрнэ
2. **Олон хувилбар** - Утас/имэйл/username 3-аас сонгоно
3. **Автомат таних** - Систем өөрөө таньж нэвтрүүлнэ
4. **Аюулгүй** - Бүх backend-үүд password шалгана
5. **Excel friendly** - Утас форматаас үл хамааран ажиллана

---

## 🔐 Аюулгүй байдал

- Нууц үг Django-н `check_password()` ашиглана (hash шалгана)
- Login attempt rate limiting нэмж болно (ирээдүйд)
- Session management Django default ашиглана
- CSRF protection идэвхтэй

---

## 📝 Сурагчдын нууц үг

**Анхны нууц үг:** Утасны сүүлийн 8 орон

Жишээ:
- Утас: `+976 9988-1234` → Нууц үг: `99881234`
- Утас: `88-00-12-34` → Нууц үг: `88001234`
- Утас: `70110205` → Нууц үг: `70110205`

**Анхаар:** Эхний нэвтрэлтийн дараа нууц үг солихыг зөвлөнө!

---

## 🎯 Одоо турших

1. ✅ Сервер ажиллаж байна: http://127.0.0.1:8000/
2. ✅ Login хуудас: http://127.0.0.1:8000/login/
3. ⏳ Нууц үг тохируулах: `python manage.py changepassword president`
4. ⏳ Нэвтрэх: утас/имэйл/username аль нэгээр

**Амжилт хүсье!** 🎉
