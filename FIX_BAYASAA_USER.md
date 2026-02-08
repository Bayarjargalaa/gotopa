# bayasaa68@gmail.com хэрэглэгчид агуулга засах эрх олгох заавар

## Асуудал
bayasaa68@gmail.com хэрэглэгч нэвтэрсэн ч засах товч (✏️) харагдахгүй байна.

## Шалтгаан
1. **Staff status** байхгүй байна ИЛИ
2. **Content Editor** бүлэгт харьяалагдаагүй байна

---

## ✅ Шийдэл 1: Админ панелаар

### 1. Superadmin-аар нэвтрэх
```
http://127.0.0.1:8000/admin/
Username: gotopa_admin (эсвэл өөр superadmin)
Password: gotopa2025
```

### 2. Хэрэглэгч засварлах
1. Зүүн цэснээс **"Хэрэглэгчид" (Users)** сонгох
2. **bayasaa68@gmail.com** эсвэл username-г хайх
3. Хэрэглэгч дээр дарж засварлах

### 3. Staff status олгох
**"Permissions"** хэсэгт:
```
☑ Staff status (Ажилтан статус)
```
✅ **Тэмдэглэх**

### 4. Content Editor group-д нэмэх
Доош scroll хийж **"Бүлгүүд" (Groups)** олох:

```
Available groups          Chosen groups
┌──────────────┐   →     ┌──────────────┐
│              │         │Content Editor│ ← Энэ байх ёстой
└──────────────┘         └──────────────┘
```

Зүүн талаас "Content Editor" сонгож баруун тал шилжүүлэх.

### 5. Хадгалах
**"Хадгалах"** товч дарах.

### 6. Тест хийх
1. bayasaa68@gmail.com-аар нэвтрэх
2. Нүүр хуудас руу очих
3. Текст дээр hover хийхэд **✏️ засах товч** харагдана

---

## ✅ Шийдэл 2: Management Command

```bash
python manage.py fix_bayasaa_user
```

Энэ нь автоматаар:
- Staff status олгоно
- Content Editor group-д нэмнэ
- Төлөв харуулна

---

## ✅ Шийдэл 3: Python Shell

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User, Group

# Хэрэглэгч олох
user = User.objects.get(email='bayasaa68@gmail.com')

# Staff эрх олгох
user.is_staff = True
user.save()

# Content Editor group-д нэмэх
group = Group.objects.get(name='Content Editor')
user.groups.add(group)

print('✓ Амжилттай!')
```

---

## 🔍 Эрх шалгах

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User

user = User.objects.get(email='bayasaa68@gmail.com')
print(f'is_staff: {user.is_staff}')  # True байх ёстой
print(f'Groups: {[g.name for g in user.groups.all()]}')  # ['Content Editor'] байх ёстой
```

---

## 📝 Засах товч харагдах нөхцөл

Template код дээр:
```django
{% if user.is_authenticated and user.is_staff %}
    <span class="editable-content" data-key="...">
        ...текст...
        <button class="edit-btn" onclick="editContent(...)">✏️</button>
    </span>
{% endif %}
```

**Хоёр нөхцөл:**
1. ✅ `user.is_authenticated` - Нэвтэрсэн байх
2. ✅ `user.is_staff` - Staff status байх

---

## ⚠️ Анхааруулга

### Superuser эрх бүү олгоорой
```
☐ Superuser status
```
Энийг тэмдэглэхгүй байх! Superuser нь бүх эрхтэй болно.

### Зөвхөн Content Editor л хангалттай
Агуулга засахад зөвхөн:
- ✅ Staff status
- ✅ Content Editor group

---

## ✅ Бүрэн шалгах жагсаалт

- [ ] Email зөв эсэх: `bayasaa68@gmail.com`
- [ ] Хэрэглэгч олдсон эсэх
- [ ] `is_staff = True`
- [ ] `is_active = True`
- [ ] Content Editor group-д харьяалагдаж байгаа эсэх
- [ ] Нэвтрэх боломжтой эсэх
- [ ] Засах товч харагдаж байгаа эсэх

---

## 🐛 Асуудал үргэлжилбэл

1. **Cache цэвэрлэх:**
   - Browser: Ctrl + Shift + R
   - Эсвэл Incognito mode ашиглах

2. **Сервер restart:**
   ```bash
   Ctrl + C
   python manage.py runserver
   ```

3. **Debug mode:**
   Browser console (F12) дээр алдаа шалгах

4. **Template шалгах:**
   `main/templates/main/home.html` файлд `{% if user.is_authenticated and user.is_staff %}` байгаа эсэх

---

Одоо `bayasaa68@gmail.com` хэрэглэгч нэвтрээд нүүр хуудас дээр текст дээр hover хийхэд засах товч харагдах болно! 🎉
