# Шинэ Цэс/Хуудас Нэмэх Заавар - HTML Эрхийн Удирдлага

## 🎯 Зарчим

Шинэ цэс нэмэхдээ **permission-based** шалгалт ашиглавал HTML дээрээс автоматаар удирдагдана.

---

## 📝 Алхам 1: Model-д Custom Permission нэмэх

Хэрэв шинэ модель үүсгэж байгаа бол:

```python
# main/models.py
class NewFeature(models.Model):
    name = models.CharField(max_length=100)
    
    class Meta:
        permissions = [
            ('can_view_newfeature', 'Шинэ модуль харах эрхтэй'),
            ('can_manage_newfeature', 'Шинэ модуль удирдах эрхтэй'),
        ]
```

Migration ажиллуулах:
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 📋 Алхам 2: menu_config.py-д цэс нэмэх

**ЗӨВХӨН permission-based шалгалт ашиглах:**

```python
# main/menu_config.py

SIDEBAR_MENU = [
    # ... бусад цэснүүд
    
    {
        'section': '🆕 Шинэ Модуль',
        'icon': 'fas fa-star',
        'permissions': [],  # Section-г item-үүдээр шүүнэ
        'items': [
            {
                'label': 'Жагсаалт',
                'url_name': 'main:newfeature_list',
                'icon': 'fas fa-list',
                'permissions': ['is_admin', 'perm:main.view_newfeature', 'perm:main.can_view_newfeature'],
                #            ^^^^^^^^    ^^^^^^^^^^^^^^^^^^^^^^^^^^    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                #            Админ OR    Django auto permission    OR  Custom permission
            },
            {
                'label': 'Шинэ үүсгэх',
                'url_name': 'main:newfeature_create',
                'icon': 'fas fa-plus',
                'permissions': ['is_admin', 'perm:main.add_newfeature', 'perm:main.can_manage_newfeature'],
            },
        ]
    },
]
```

**⚠️ ХЭРГҮЙ:**
- ❌ `role:MANAGER` - Хатуу код, HTML дээрээс удирдагдахгүй
- ❌ `group:БүлгийнНэр` - Бүлэгт харьяалагдсан эсэхийг л шалгана, эрхүүдийг харгалзахгүй

**✅ АШИГЛАХ:**
- ✅ `is_admin` - Админууд бүгдэд харагдана
- ✅ `is_accountant` - Нягтлан бодогчдод харагдана
- ✅ `is_teacher` - Багш нарт харагдана
- ✅ `perm:main.CODENAME` - Тодорхой эрхтэй хүмүүст л харагдана

---

## 🔐 Алхам 3: View функцүүдэд эрх шалгах

**Зарчим:** menu_config.py-тэй ижил эрх шалгалт хийх

```python
# main/views.py

@login_required
def newfeature_list(request):
    """Шинэ модулийн жагсаалт"""
    user = request.user
    
    # Menu-тэй ижил эрх шалгалт
    has_access = (
        user.profile.is_admin or
        user.has_perm('main.view_newfeature') or
        user.has_perm('main.can_view_newfeature')
    )
    
    if not has_access:
        messages.error(request, 'Энэ хуудсыг харах эрх танд байхгүй.')
        return redirect('main:dashboard')
    
    # View код...
    items = NewFeature.objects.all()
    return render(request, 'main/newfeature_list.html', {'items': items})


@login_required
def newfeature_create(request):
    """Шинэ модуль үүсгэх"""
    user = request.user
    
    has_access = (
        user.profile.is_admin or
        user.has_perm('main.add_newfeature') or
        user.has_perm('main.can_manage_newfeature')
    )
    
    if not has_access:
        messages.error(request, 'Энэ үйлдлийг хийх эрх танд байхгүй.')
        return redirect('main:newfeature_list')
    
    # Create код...
```

---

## 🌐 Алхам 4: HTML дээрээс эрх өгөх

### Вариант 1: Эрхийн бүлэг дээр

1. Dashboard → Тохиргоо → **Эрхийн бүлгүүд (HTML)**
2. "Менежер" эсвэл бусад бүлэг сонгох
3. ✏️ Засах
4. Эрхүүд сонгох:
   - ✅ `Can view new feature`
   - ✅ `Шинэ модуль харах эрхтэй` (custom)
5. 💾 Хадгалах

### Вариант 2: Хэрэглэгч дээр

1. Сурагчдын жагсаалт → 🛡️ Эрхийн бүлэг товч
2. Эрхийн бүлэг сонгох
3. 💾 Хадгалах

### Үр дүн:

- F5 дарахад **шууд** цэс гарч ирнэ!
- Эрх хасвал **шууд** цэс алга болно!

---

## 💡 Жишээ: "Санхүүгийн тайлан" модуль нэмэх

### 1. Permission үүсгэх

Хэрэв шинэ модель байхгүй, харин одоо байгаа модель ашиглана бол:

```python
# main/models.py - одоо байгаа модель дээр
class BankTransaction(models.Model):
    # ... existing fields
    
    class Meta:
        permissions = [
            ('can_view_financial_report', 'Санхүүгийн тайлан харах эрхтэй'),
        ]
```

### 2. menu_config.py

```python
{
    'section': '💰 Санхүү',
    'icon': 'fas fa-coins',
    'permissions': [],  # Item шүүлт
    'items': [
        {
            'label': 'Банкны гүйлгээ',
            'url_name': 'main:bank_transaction_list',
            'icon': 'fas fa-university',
            'permissions': ['is_admin', 'is_accountant', 'perm:main.view_banktransaction'],
        },
        {
            'label': 'Санхүүгийн тайлан',
            'url_name': 'main:financial_report',
            'icon': 'fas fa-chart-pie',
            'permissions': ['is_admin', 'is_accountant', 'perm:main.can_view_financial_report'],
        },
    ]
},
```

### 3. View

```python
@login_required
def financial_report(request):
    has_access = (
        user.profile.is_admin or
        user.profile.is_accountant or
        user.has_perm('main.can_view_financial_report')
    )
    
    if not has_access:
        messages.error(request, 'Санхүүгийн тайлан харах эрх байхгүй.')
        return redirect('main:dashboard')
    
    # Report код...
```

### 4. HTML дээрээс

"Харагч" бүлэгт `can_view_financial_report` эрх өгвөл тайлан харна!

---

## 🔄 Workflow Хураангуй

```
Шинэ хуудас нэмэх
    ↓
1. Model/Permission үүсгэх (migration)
    ↓
2. menu_config.py-д perm: ашиглан нэмэх
    ↓
3. View-д ижил эрх шалгалт хийх
    ↓
4. HTML дээрээс бүлэгт эрх өгөх
    ↓
5. F5 → Цэс гарч ирнэ! ✅
```

---

## 📊 Эрхийн төрлүүд

| Эрх | Хэзээ үүснэ | Жишээ |
|-----|-------------|-------|
| **Django auto** | Model үүссэн үед | `view_product`, `add_sale`, `change_course` |
| **Custom** | Meta.permissions | `can_view_inventory`, `can_manage_inventory` |
| **Property** | Code дотор | `is_admin`, `is_accountant`, `is_teacher` |

---

## ⚠️ Анхаарах зүйлс

### 1. Эрх нэр тохирох ёстой

Menu болон View-д **яг ижил** эрх шалгалт хийх:

```python
# menu_config.py
'permissions': ['perm:main.view_product']

# views.py
user.has_perm('main.view_product')  # ← Яг ижил!
```

### 2. OR логик

Django permission нь **OR** логиктэй:

```python
'permissions': ['is_admin', 'perm:main.view_product']
# Админ ЭСВЭЛ view_product эрхтэй бол харагдана
```

### 3. AND логик хэрэгтэй бол

View дотор өөрөө шалгах:

```python
has_access = (
    user.profile.is_admin and  # ← AND
    user.has_perm('main.can_manage_sensitive_data')
)
```

---

## 🎓 Практик дасгал

### Дасгал: "Хэрэглэгчийн үйл ажиллагааны лог" нэмэх

**1. Permission үүсгэх:**
```python
class UserProfile(models.Model):
    # ... existing
    
    class Meta:
        permissions = [
            ('can_view_user_logs', 'Хэрэглэгчийн лог харах эрхтэй'),
        ]
```

**2. menu_config.py:**
```python
{
    'label': 'Үйл ажиллагааны лог',
    'url_name': 'main:user_logs',
    'icon': 'fas fa-history',
    'permissions': ['is_admin', 'perm:main.can_view_user_logs'],
},
```

**3. View:**
```python
@login_required
def user_logs(request):
    has_access = (
        request.user.profile.is_admin or
        request.user.has_perm('main.can_view_user_logs')
    )
    
    if not has_access:
        return redirect('main:dashboard')
    
    # Logs...
```

**4. HTML:**
- "Менежер" бүлэгт `can_view_user_logs` эрх өгөх
- F5 → Цэс гарна!

---

## 🚀 Дүгнэлт

**Одооноос хойш:**

✅ Шинэ цэс/хуудас нэмэхдээ `perm:` ашиглах  
✅ View-д ижил эрх шалгалт хийх  
✅ HTML дээрээс эрх өгөх  
✅ F5 дарахад автоматаар ажиллана  
✅ Код өөрчлөхгүй!  

**Бүү ашигла:**

❌ `role:MANAGER` - Хатуу код  
❌ `group:БүлгийнНэр` - Бүлгийн эрхүүдийг харгалзахгүй  

**Permission-based зарчим нь:**
- 🔄 Динамик
- 🎨 Уян хатан
- 🚀 Хурдан
- 💪 Хүчирхэг
