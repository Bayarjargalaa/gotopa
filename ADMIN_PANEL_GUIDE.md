# Админ панелийн хэрэглэгч удирдлага

## 2 хэсгийн ялгаа

### 1. **Users (Хэрэглэгчид)** - Django үндсэн User model

**Байршил:** Authentication and Authorization > Users

**Юу хадгалдаг:**
- ✅ Нэвтрэх мэдээлэл (username, password)
- ✅ Имэйл хаяг
- ✅ Нэр (first_name, last_name)
- ✅ Админ эрхүүд (is_staff, is_superuser, is_active)
- ✅ Groups (бүлгүүд)
- ✅ User permissions (тусгай эрхүүд)
- ✅ Сүүлд нэвтэрсэн огноо

**Хэзээ ашиглах:**
- 🔑 Нууц үг солих
- 🔐 Админ панел руу нэвтрэх эрх олгох (is_staff = True)
- 👥 Бүлэгт нэмэх (Groups)
- ⚙️ Тусгай эрх олгох (User permissions)

**Онцлог:**
- User үүсгэхэд **UserProfile автоматаар** үүснэ (signal ажиллана)
- Хэрэглэгчийн Монгол нэр, утас, эрх зэргийг энд харж болно (inline талбар)

---

### 2. **UserProfile (Хэрэглэгчдийн мэдээлэл)** - Готопагийн өргөтгөл

**Байршил:** Main > Хэрэглэгчдийн мэдээлэл

**Юу хадгалдаг:**
- 📝 Монгол нэр
- 📞 Утас
- 👤 Роль (PRESIDENT, MANAGER, TEACHER, STUDENT)
- 📅 Төрсөн огноо
- 🚻 Хүйс
- 📍 Хаяг, хот, дүүрэг
- 🎓 Элсэлтийн огноо
- 🖼️ Зураг
- 📝 Тэмдэглэл

**Хэзээ ашиглах:**
- 🎭 Роль солих (STUDENT → TEACHER)
- 📊 Хэрэглэгчдийг роль, хотоор нь шүүж харах
- 📱 Утасны дугаар засах
- 📋 Монгол нэр, хаяг засах

**Онцлог:**
- User-тэй 1:1 харилцаатай (нэг User = нэг UserProfile)
- **Энд роль солиход цэс автоматаар өөрчлөгдөнө**

---

## Хэрхэн ажилладаг

```
User (Django үндсэн)         UserProfile (Готопагийн өргөтгөл)
├─ username: president       ├─ mongolian_name: Доржийн Бат
├─ email: pres@gotopa.mn     ├─ phone: 99001234
├─ is_staff: True            ├─ role: PRESIDENT
├─ is_superuser: True        ├─ city: Улаанбаатар
└─ groups: []                └─ is_active_student: True
```

**Signal автоматжуулалт:**
```python
# models.py дээр
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)  # Автоматаар үүснэ
```

---

## Цэс харах эрхийг хэрхэн тохируулах

### Арга 1: Роль солих (Хурдан арга)

**Алхам 1:** Main > Хэрэглэгчдийн мэдээлэл  
**Алхам 2:** Хэрэглэгч сонгох  
**Алхам 3:** **Role** талбарыг солих:
- `STUDENT` → Зөвхөн өөрийн мэдээлэл харна
- `TEACHER_BEGINNER/INTERMEDIATE/ADVANCED` → Сургалтын цэс харна
- `ACCOUNTANT` → Санхүүгийн цэс харна
- `MANAGER` → Бараа материал, санхүүгийн цэс харна
- `PRESIDENT/DIRECTOR` → Бүх цэс харна

**Алхам 4:** Хадгалах

**Үр дүн:**
```python
# menu_config.py дээр автомат шалгагдана
'permissions': ['is_admin', 'role:MANAGER']
# MANAGER роль бол цэс харагдана
```

---

### Арга 2: Бүлэгт нэмэх (Илүү уян хатан)

**Алхам 1:** Authentication > Users > Хэрэглэгч сонгох  
**Алхам 2:** Доошоо scroll хийж **Permissions** хэсэг рүү очих  
**Алхам 3:** **Staff status** ☑️ шалгах (админ панел руу нэвтрэх эрх)  
**Алхам 4:** **Groups** дээр шаардлагатай бүлгүүдийг сонгох:

```
Available groups          Chosen groups
─────────────────────    ─────────────────────
Агуулахын менежер    →→→  ✓ Агуулахын менежер
Санхүүчин            →→→  
Сургалтын менежер         
Content Editor            
Харагч                    
```

**Алхам 5:** Хадгалах

**Үр дүн:**
```python
# menu_config.py дээр автомат шалгагдана
'permissions': ['group:Агуулахын менежер']
# Энэ бүлэгт харьяалагдсан бол цэс харагдана
```

---

### Арга 3: Тусгай эрх олгох (Өвөрмөц тохиолдолд)

**Алхам 1:** Authentication > Users > Хэрэглэгч сонгох  
**Алхам 2:** **User permissions** хэсэгт тусгай эрхүүд сонгох:

```
Available user permissions        Chosen permissions
───────────────────────────────  ───────────────────────────────
main | product | Can add...   →→→  ✓ main | product | Can view...
main | product | Can change...→→→  ✓ main | product | Can add...
main | product | Can delete...    
```

**Алхам 3:** Хадгалах

**Үр дүн:**
```python
# menu_config.py дээр автомат шалгагдана
'permissions': ['perm:main.add_product']
# Энэ эрхтэй бол цэс харагдана
```

---

## Практик жишээнүүд

### Жишээ 1: Агуулахын ажилтан

**Зорилго:** Зөвхөн бараа материалын цэс харуулах

**Хувилбар A - Роль ашиглах:**
1. Main > Хэрэглэгчдийн мэдээлэл > Хэрэглэгч сонгох
2. Role → `MANAGER`
3. Хадгалах

**Хувилбар B - Бүлэг ашиглах (илүү сайн):**
1. Users > Хэрэглэгч сонгох
2. Staff status ☑️
3. Groups → `Агуулахын менежер`
4. Хадгалах

**Харагдах цэс:**
```
✅ Хувийн
✅ 📦 Бараа материал
✅ 👥 Харилцагч
✅ 📊 Тайлан
❌ Санхүү
❌ Сургалт
```

---

### Жишээ 2: Санхүүгийн ажилтан

**Хувилбар A - Роль:**
1. UserProfile > Role → `ACCOUNTANT`

**Хувилбар B - Бүлэг:**
1. Users > Groups → `Санхүүчин`
2. Staff status ☑️

**Харагдах цэс:**
```
✅ Хувийн
✅ Санхүү (бүх санхүүгийн цэс)
✅ 👥 Харилцагч (харагч эрхээр)
❌ Бараа материал
❌ Сургалт
```

---

### Жишээ 3: Зөвхөн тайлан харагч

1. Users > Хэрэглэгч сонгох
2. Staff status ☑️
3. Groups → `Харагч`
4. Хадгалах

**Харагдах цэс:**
```
✅ Хувийн
✅ 📊 Тайлан (зөвхөн унших)
❌ Бусад засварлах боломжууд
```

---

### Жишээ 4: Олон эрхтэй хэрэглэгч

Агуулах + Санхүү хоёуланг нь харуулах:

1. Users > Хэрэглэгч сонгох
2. Staff status ☑️
3. Groups → `Агуулахын менежер`, `Санхүүчин` (хоёуланг сонгох)
4. Хадгалах

**Харагдах цэс:**
```
✅ Хувийн
✅ Санхүү
✅ 📦 Бараа материал
✅ 👥 Харилцагч
✅ 📊 Тайлан
❌ Сургалт
```

---

## Цэс харагдалтын логик

### Шалгалтын дараалал:

1. **Superuser шалгах** → Тийм бол бүх цэс харагдана
2. **Эрхүүдийг нэг нэгээр шалгах** (OR логик):
   - `is_admin` (UserProfile.is_admin)
   - `role:MANAGER` (UserProfile.role == 'MANAGER')
   - `group:Агуулахын менежер` (user.groups.filter...)
   - `perm:main.add_product` (user.has_perm...)
3. **Аль нэгийг хангасан бол** → Цэс харагдана

### Код жишээ:

```python
# main/menu_config.py дээр
def user_has_permission(user, permissions):
    if user.is_superuser:
        return True  # Бүх цэс
    
    for permission in permissions:
        if permission == 'is_admin' and user.profile.is_admin:
            return True
        if permission.startswith('role:'):
            role_name = permission.split(':')[1]
            if user.profile.role == role_name:
                return True
        if permission.startswith('group:'):
            group_name = permission.split(':')[1]
            if user.groups.filter(name=group_name).exists():
                return True
    
    return False
```

---

## Түгээмэл асуултууд

### Q: User эсвэл UserProfile дээр роль солих нь илүү үү?

**A:** UserProfile дээр роль солих нь илүү хялбар. Гэхдээ **бүлэг (Groups) ашиглах нь илүү уян хатан**:
- ✅ Олон эрх нэгтгэж болно
- ✅ Эрхүүд өөрчлөгдөхөд бүх хэрэглэгч автоматаар өөрчлөгдөнө
- ✅ Админ панелаас эрхүүдийг хялбар засах

### Q: Staff status яагаад шаардлагатай вэ?

**A:** Django-ийн дүрэм:
- `is_staff=True` гэсэн хэрэглэгч л админ панел руу нэвтрэх эрхтэй
- Groups эсвэл User permissions байсан ч `is_staff=False` бол админ панел руу нэвтрэх боломжгүй

### Q: Цэс шууд идэвхжих үү?

**A:** Тийм! Хэрэглэгч дахин нэвтрэх шаардлагагүй. Цэс автоматаар шинэчлэгдэнэ.

### Q: Роль солиход sidebar өөрчлөгдөх үү?

**A:** Тийм! `menu_config.py` роль шалгана:
```python
'permissions': ['is_admin', 'role:MANAGER']
```

### Q: 2 хэсгийн аль дээр ажиллах нь илүү сайн вэ?

**A:** 
- **Users** - Эрх, Groups, нууц үг
- **UserProfile** - Монгол нэр, утас, роль

**Зөвлөмж:** Ихэнх тохиолдолд **Users** дээр ажиллах нь илүү (бүгдийг нэг дор харж болно - inline талбараар).

---

## Хураангуй

### Цэс тохируулах 3 арга:

| Арга | Хэзээ ашиглах | Онцлог |
|------|---------------|--------|
| **Роль** | Готопагийн үндсэн эрхүүд | Хялбар, гэхдээ хязгаарлагдмал |
| **Бүлэг** | Уян хатан эрх удирдлага | ⭐ Санал болгож байна |
| **Тусгай эрх** | Өвөрмөц тохиолдол | Нарийн тохируулга |

### Санал болгож байгаа ажлын урсгал:

1. **Бүлэг үүсгэх:** `python manage.py create_permission_groups`
2. **Хэрэглэгчдэд бүлэг олгох:** Users > Groups сонгох
3. **Staff status идэвхжүүлэх:** is_staff ☑️
4. **Тест хийх:** Нэвтрэх > Sidebar цэс шалгах

Илүү дэлгэрэнгүй: [PERMISSION_MANAGEMENT.md](PERMISSION_MANAGEMENT.md)
