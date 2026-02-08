# 📝 Хуудасны агуулга удирдах систем - Ашиглах заавар

## Тойм

Вэбсайтын бүх текст, гарчиг, тайлбарыг **код засалгүйгээр** database-аас удирдах систем. Админ эрхтэй хэрэглэгч Django админ панелаар дамжуулан агуулга засах боломжтой.

---

## 🚀 Эхлэх

### 1. Системийг суулгах

```bash
# Migration ажиллуулах
python manage.py makemigrations
python manage.py migrate

# Анхдагч агуулга үүсгэх
python manage.py init_page_content

# Content Editor бүлэг үүсгэх
python manage.py setup_content_editor

# (Сонголт) Жишээ хэрэглэгч үүсгэх
python manage.py create_content_editor_user
```

### 2. Эрхийн түвшин

| Эрх | Тайлбар | Хандах хэрэгсэл |
|-----|---------|----------------|
| **Superadmin** | Бүх эрхтэй | Бүх админ панел |
| **Content Editor** | Зөвхөн агуулга засах | Хуудасны агуулгууд |
| **Энгийн хэрэглэгч** | Вэб үзэх, бүртгүүлэх | Нүүр хуудас |

---

## 👤 Хэрэглэгчдэд эрх олгох

### Арга 1: Admin панелаар (UI)

**Дэлгэрэнгүй:** [CONTENT_EDITOR_PERMISSION.md](CONTENT_EDITOR_PERMISSION.md)

1. `/admin/` руу нэвтрэх (superadmin)
2. **Хэрэглэгчид** → Хэрэглэгч сонгох
3. **Staff status** тэмдэглэх ☑
4. **Бүлгүүд** → **Content Editor** нэмэх
5. Хадгалах

### Арга 2: Python Shell (олон хэрэглэгч)

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User, Group

# Content Editor group
group = Group.objects.get(name='Content Editor')

# Хэрэглэгчдэд эрх олгох
users = ['user1', 'user2', 'user3']
for username in users:
    user = User.objects.get(username=username)
    user.is_staff = True
    user.groups.add(group)
    user.save()
```

### Арга 3: Command ашиглах (жишээ хэрэглэгч)

```bash
python manage.py create_content_editor_user
```

**Үүсгэсэн:**
- Username: `content_editor`
- Password: `gotopa2025`
- Эрх: Content Editor

---

## ✏️ Агуулга засах

### Админаар нэвтрэх

```
URL: http://127.0.0.1:8000/admin/
Нэвтрэх: Content Editor эрхтэй хэрэглэгч
```

### Текст засах үе шат

**Дэлгэрэнгүй:** [CONTENT_EDITING_GUIDE.md](CONTENT_EDITING_GUIDE.md)

1. **"Хуудасны агуулгууд"** цэс сонгох
2. Засах текст дээр дарах
3. **"Агуулга"** талбарыг засах
4. **"Хадгалах"** товч дарах
5. Вэб хуудсаа F5 дарж reload хийх

### Нүүр хуудасны агуулга

| Түлхүүр (Key) | Тайлбар | Анхдагч утга |
|--------------|---------|--------------|
| `home_hero_subtitle` | Hero дэд гарчиг | "Готопа бясалгал бол" |
| `home_hero_title` | Hero үндсэн гарчиг | "Хүн төрөлхтөнд барих бэлэг" |
| `home_hero_description` | Hero тайлбар | "Өндөр давтамжийн бясалгал" |
| `home_hero_btn_learn` | Дэлгэрэнгүй товч | "Дэлгэрэнгүй" |
| `home_hero_btn_register` | Бүртгүүлэх товч | "Бүртгүүлэх" |
| `home_feature1_title` | Онцлог 1 гарчиг | "Бясалгал гэж юу вэ?" |
| `home_feature1_desc` | Онцлог 1 тайлбар | "Бид хэрхэн бясалгал хийдэг вэ?" |
| `home_feature2_title` | Онцлог 2 гарчиг | "Ном" |
| `home_feature2_desc` | Онцлог 2 тайлбар | "Хэвлэгдэн гарсан номууд" |
| `home_feature3_title` | Онцлог 3 гарчиг | "Тайлбар үгс" |
| `home_feature3_desc` | Онцлог 3 тайлбар | "Сайтад орсон үгсийн тайлбарууд" |
| `home_about_subtitle` | Бидний тухай дэд гарчиг | "Бясалгалыг сонгох давуу талууд" |
| `home_about_title` | Бидний тухай гарчиг | "Оюун санааны амар амгаланд..." |
| `home_about_desc` | Бидний тухай тайлбар | "Бид таньд бясалгалын мэдлэгийг..." |
| `home_about_benefit1` | Давуу тал 1 | "Гүрү Готопа багш заана" |
| `home_about_benefit2` | Давуу тал 2 | "Анхан шатны 3 сарын сургалт..." |
| `home_about_benefit3` | Давуу тал 3 | "Хичээллэх тав тухтай орчин" |
| `home_about_benefit4` | Давуу тал 4 | "Баталгаажсан үр дүн" |

---

## 🔒 Аюулгүй байдал

### Анхааруулга

| Хийх | Хийхгүй |
|------|---------|
| ✓ Зөвхөн "Агуулга" талбарыг засах | ✗ "Түлхүүр" (Key) засах |
| ✓ Монгол үсгээр бичих | ✗ JavaScript код оруулах |
| ✓ Товч, ойлгомжтой текст | ✗ Хэт урт текст бичих |
| ✓ Content Editor эрх олгох | ✗ Superuser эрх олгох (шаардлагагүй) |

### Эрх хураах

Хэрэглэгчээс эрх хураах:

```python
user = User.objects.get(username='username')
user.groups.clear()  # Бүх бүлгээс хасах
# эсвэл
user.is_staff = False  # Admin панел хаах
user.save()
```

---

## 📁 Файлууд

| Файл | Зориулалт |
|------|-----------|
| `models.py` | PageContent model (database бүтэц) |
| `admin.py` | PageContentAdmin (админ панелын тохиргоо) |
| `views.py` | home() view (template-д агуулга дамжуулах) |
| `home.html` | Template (агуулга харуулах) |
| `management/commands/init_page_content.py` | Анхдагч агуулга үүсгэх |
| `management/commands/setup_content_editor.py` | Content Editor бүлэг үүсгэх |
| `management/commands/create_content_editor_user.py` | Жишээ хэрэглэгч үүсгэх |

---

## 🛠 Командууд

```bash
# Анхдагч тохиргоо
python manage.py init_page_content          # 18 агуулга үүсгэх
python manage.py setup_content_editor       # Content Editor бүлэг + эрх

# Хэрэглэгч удирдах
python manage.py create_content_editor_user # Жишээ хэрэглэгч үүсгэх
python manage.py createsuperuser            # Superadmin үүсгэх
python manage.py changepassword username    # Нууц үг солих

# Database
python manage.py makemigrations             # Migration үүсгэх
python manage.py migrate                    # Migration ажиллуулах

# Сервер
python manage.py runserver                  # Сервер асаах
```

---

## 🐛 Алдааны шийдэл

### "Хуудасны агуулгууд" харагдахгүй байна

```bash
# 1. Migration ажиллуулах
python manage.py migrate

# 2. Бүлэг дахин үүсгэх
python manage.py setup_content_editor

# 3. Staff status шалгах
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username='username')
>>> user.is_staff
True  # Энэ нь True байх ёстой
```

### Агуулга вэб дээр харагдахгүй байна

1. ✓ Database-д агуулга байгаа эсэхийг шалгах
2. ✓ `is_active=True` эсэхийг шалгах
3. ✓ Template-д `page_contents` context байгаа эсэхийг шалгах
4. ✓ Түлхүүр (key) зөв эсэхийг шалгах

### Permission denied алдаа

```python
# User-д шууд эрх олгох
user = User.objects.get(username='username')
user.is_staff = True
user.save()

# Group-д нэмэх
from django.contrib.auth.models import Group
group = Group.objects.get(name='Content Editor')
user.groups.add(group)
```

---

## 📚 Холбоос

- **Админд эрх олгох:** [CONTENT_EDITOR_PERMISSION.md](CONTENT_EDITOR_PERMISSION.md)
- **Агуулга засах:** [CONTENT_EDITING_GUIDE.md](CONTENT_EDITING_GUIDE.md)
- **Готопа системийн заавар:** [LOGIN_GUIDE.md](LOGIN_GUIDE.md)

---

## ✅ Тест хэрэглэгчид

| Username | Password | Эрх | Зориулалт |
|----------|----------|-----|-----------|
| `gotopa_admin` | `gotopa2025` | Superadmin | Бүх эрхтэй |
| `content_editor` | `gotopa2025` | Content Editor | Агуулга засах |
| `president` | `gotopa2025` | Admin | Удирдлага |

---

**Анхааруулга:** Production орчинд нууц үгийг өөрчилж, аюулгүй байдлыг хангана уу!
