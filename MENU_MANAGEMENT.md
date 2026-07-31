# Цэсний удирдлага - Хэрэглэгчдэд харагдах цэс

## Тойм

Систем одоо **динамик цэс (menu-driven navigation)** болсон. Цэсүүд `main/menu_config.py` файлд тодорхойлогдож, хэрэглэгчийн эрхээр автоматаар шүүгдэнэ.

## Давуу тал

✅ **Код засахгүй** - Цэс нэмэх/хасах хялбар (зөвхөн menu_config.py засах)  
✅ **Эрхээр автомат шүүх** - Хэрэглэгч зөвхөн өөрт зориулсан цэсийг харна  
✅ **Төвлөрсөн удирдлага** - Бүх цэс нэг газар  
✅ **Group permission дэмжлэг** - Django Groups-тэй бүрэн уялдаатай  
✅ **Өргөтгөх боломжтой** - Шинэ эрхийн төрөл нэмэх хялбар

## Файлын бүтэц

### 1. main/menu_config.py

Цэсний бүх тохиргоо энд байна:

```python
SIDEBAR_MENU = [
    {
        'section': 'Санхүү',  # Бүлгийн гарчиг
        'icon': 'fas fa-coins',
        'permissions': ['is_admin', 'is_accountant'],  # Харагдах эрх
        'items': [
            {
                'label': 'Журнал',
                'url_name': 'main:journal_list',
                'icon': 'fas fa-book',
                'permissions': ['is_admin', 'is_accountant'],
            },
            # ...
        ]
    },
]
```

### 2. main/context_processors.py

`user_menu` автоматаар бүх template-д дамжна:

```python
from .menu_config import get_user_menu

def page_content_processor(request):
    user_menu = []
    if request.user.is_authenticated:
        user_menu = get_user_menu(request.user)
    
    return {
        'user_menu': user_menu,
        # ...
    }
```

### 3. main/templates/main/base.html

Template цэсийг loop-оор харуулна:

```django
{% for section in user_menu %}
<div class="mb-6">
    <h3>{{ section.section }}</h3>
    {% for item in section.items %}
    <a href="{% url item.url_name %}">
        <i class="{{ item.icon }}"></i>
        {{ item.label }}
    </a>
    {% endfor %}
</div>
{% endfor %}
```

## Эрхийн төрөл

### Үндсэн эрхүүд

| Эрх | Тайлбар |
|-----|---------|
| `authenticated` | Нэвтэрсэн бүх хэрэглэгч |
| `is_admin` | Админ эрхтэй (UserProfile.is_admin) |
| `is_accountant` | Нягтлан бодогч (UserProfile.is_accountant) |
| `is_teacher` | Багш (UserProfile.is_teacher) |
| `is_staff` | Django staff статустай |
| `is_superuser` | Superuser |

### Role-based эрхүүд

```python
'permissions': ['role:MANAGER']  # Тодорхой role
'permissions': ['role:ACCOUNTANT']
```

### Group-based эрхүүд

```python
'permissions': ['group:Агуулахын менежер']  # Django Groups
'permissions': ['group:Санхүүчин']
```

### Django permission эрхүүд

```python
'permissions': ['perm:main.add_product']  # Тусгай permission
'permissions': ['perm:main.view_banktransaction']
```

### OR логик (аль нэгийг хангавал)

```python
'permissions': ['is_admin', 'is_accountant', 'group:Санхүүчин']
# Админ ЭСВЭЛ нягтлан ЭСВЭЛ Санхүүчин бүлэгт харьяалагдсан бол харагдана
```

## Цэс нэмэх

### Жишээ 1: Шинэ бүлэг нэмэх

`main/menu_config.py` дээр SIDEBAR_MENU-д нэмэх:

```python
SIDEBAR_MENU = [
    # ... бусад бүлгүүд
    {
        'section': '📧 Имэйл',
        'icon': 'fas fa-envelope',
        'permissions': ['is_admin', 'group:Маркетинг'],
        'items': [
            {
                'label': 'Имэйл илгээх',
                'url_name': 'main:send_email',
                'icon': 'fas fa-paper-plane',
                'permissions': ['is_admin', 'group:Маркетинг'],
            },
            {
                'label': 'Жагсаалт',
                'url_name': 'main:email_list',
                'icon': 'fas fa-list',
                'permissions': ['is_admin', 'group:Маркетинг'],
            },
        ]
    },
]
```

### Жишээ 2: Өнгөт цэс нэмэх

```python
{
    'label': 'Яаралтай гүйлгээ',
    'url_name': 'main:urgent_transactions',
    'icon': 'fas fa-exclamation-triangle',
    'color': 'text-red-600 hover:bg-red-600',  # Улаан өнгө
    'permissions': ['is_accountant'],
},
```

### Жишээ 3: Гадаад линк нэмэх

```python
{
    'label': 'Google Analytics',
    'url_name': 'https://analytics.google.com',
    'icon': 'fas fa-chart-pie',
    'external': True,  # URL template tag ашиглахгүй
    'permissions': ['is_admin'],
},
```

## Цэс засах

### 1. Эрх өөрчлөх

```python
# Өмнө: Зөвхөн админ харна
'permissions': ['is_admin']

# Одоо: Агуулахын менежер ч харна
'permissions': ['is_admin', 'group:Агуулахын менежер']
```

### 2. Цэс нууцлах

```python
# Бүлэг бүхэлд нь нууцлах
{
    'section': 'Сургалт',
    'permissions': [],  # Эсвэл хоосон list
    'items': []
}

# Эсвэл SIDEBAR_MENU-аас устгах
```

### 3. Дараалал солих

```python
SIDEBAR_MENU = [
    # 1-р байрлалд Санхүү гаргах
    {...},  # Санхүү
    # 2-р байрлалд Бараа материал
    {...},  # Бараа материал
]
```

## Тестлэх

### 1. Тодорхой эрхтэй хэрэглэгч үүсгэх

```python
python manage.py shell
```

```python
from django.contrib.auth.models import User, Group
from main.models import UserProfile

# Агуулахын менежер үүсгэх
user = User.objects.create_user('warehouse1', password='test123')
user.is_staff = True
user.save()

# Бүлэгт нэмэх
warehouse_group = Group.objects.get(name='Агуулахын менежер')
user.groups.add(warehouse_group)

print(f"Нэвтрэх: warehouse1 / test123")
```

### 2. Цэс харагдаж байгаа эсэхийг шалгах

```python
from main.menu_config import get_user_menu

user_menu = get_user_menu(user)
for section in user_menu:
    print(f"\n📁 {section['section']}")
    for item in section['items']:
        print(f"  ├─ {item['label']}")
```

## Түгээмэл асуултууд

**Q: Цэс өөрчлөлт хэзээ идэвхжих вэ?**  
A: Код өөрчлөхөд шууд идэвхжинэ. Server дахин ажиллуулах шаардлагагүй (development mode-д).

**Q: Нэг хэрэглэгч хоёр эрхтэй бол?**  
A: Аль нэгийг хангавал цэс харагдана (OR логик).

**Q: Тодорхой цэс нуухдаа цэсний дугаар алдагдах уу?**  
A: Үгүй, бусад цэс автоматаар дээш шилжинэ.

**Q: Header цэс (дээд талын цэс) ч мөн адил ажиллах уу?**  
A: Одоогоор зөвхөн sidebar дээр. Header цэс тусдаа тохируулагдсан.

**Q: Icon өөрчлөх**  
A: Font Awesome icon class солих: `'icon': 'fas fa-crown'`

**Q: Шинэ эрхийн төрөл нэмэх**  
A: `menu_config.py` дээрх `user_has_permission()` функц руу нэмэх.

## Анхааруулга

⚠️ **menu_config.py засахдаа анхаарах:**
- URL name алдаатай байвал цэс дарахад 404 гарна
- Permission нэр буруу бол цэс харагдахгүй
- Section хоосон бол бүх хэрэглэгчид харагдана

⚠️ **Эрхийн логик:**
- Хоосон permissions = Бүх нэвтэрсэн хэрэглэгч харна
- Superuser = Бүх цэс харна (эрхээс үл хамааран)

## Жишээ сценари

### Сценари 1: Агуулахын менежер цэсүүд

Хэрэглэгч:
- Groups: "Агуулахын менежер"
- is_staff: True

Харагдах цэс:
```
✅ Хувийн
✅ 📦 Бараа материал
✅ 👥 Харилцагч
✅ 📊 Тайлан
❌ Санхүү (эрх байхгүй)
❌ Сургалт (эрх байхгүй)
```

### Сценари 2: Админ бүх цэс

Хэрэглэгч:
- UserProfile.role: PRESIDENT эсвэл is_superuser=True

Харагдах цэс:
```
✅ Бүх цэс харагдана
```

### Сценари 3: Зөвхөн тайлан харагч

Хэрэглэгч:
- Groups: "Харагч"
- is_staff: True

Харагдах цэс:
```
✅ Хувийн
✅ 📊 Тайлан (view-only)
❌ Бусад засварлах цэсүүд
```
