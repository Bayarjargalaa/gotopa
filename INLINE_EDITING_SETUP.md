# Inline Content Editing - Бүрэн тохиргоо

## Ерөнхий мэдээлэл

**Content Editor** эрхтэй хэрэглэгчид одоо **БҮХ ХУУДСУУД** дээр контентийг шууд засах боломжтой боллоо!

### Юу хийгдсэн бэ?

1. ✅ **Context Processor** - Бүх template-д автоматаар `page_contents` болон `can_edit_content` дамжуулдаг
2. ✅ **Template Tag Library** - `{% load content_tags %}` ашиглан `{% editable 'key' 'default' %}` tag
3. ✅ **AJAX API** - `/api/update-content/` endpoint контент хадгалахад
4. ✅ **Inline Editing UI** - Modal popup, hover эффект, засах товчлуур
5. ✅ **42 PageContent** - Database-д бүх хуудсуудын анхдагч контент
6. ✅ **10 Template файл шинэчилсэн** - Editable tags нэмсэн

## Засагдсан Template файлууд

### ✅ Шинэчилсэн хуудсууд (editable tags нэмсэн):

1. **about.html** - Танилцуулга хуудас
2. **contact.html** - Холбоо барих
3. **courses.html** - Бясалгалын сургалтууд
4. **beginner_meditation.html** - Анхан шатны бясалгал
5. **products.html** - Бүтээгдэхүүн
6. **books.html** - Номууд
7. **travel.html** - Аялал
8. **gotopa_meditation.html** - Готопа бясалгал гэж юу вэ?
9. **guru_gotopa.html** - Гүрү Готопа багш
10. **meditation_center.html** - Бясалгалын төв
11. **news.html** - Мэдээ мэдээлэл
12. **vip_meditation.html** - Зуны VIP бясалгал
13. **home.html** - Нүүр хуудас (manual conditional wrappers)

### 📝 Template загвар:

```django
{% extends 'main/base.html' %}
{% load static %}
{% load content_tags %}  <!-- ЭНЭ МӨРИЙГ НЭМЭХ -->

{% block title %}Page Title{% endblock %}

{% block content %}
<section>
    <h1>{% editable 'page_title' 'Default Title' %}</h1>
    <p>{% editable 'page_subtitle' 'Default Subtitle' %}</p>
</section>
{% endblock %}
```

## Database агуулга (PageContent)

### 🗄️ Үүсгэсэн контентууд:

```bash
python manage.py init_page_content      # 18 нүүр хуудасны контент
python manage.py init_all_content       # 24 бусад хуудсын контент
```

### Нийт 42 PageContent:

**Нүүр хуудас (18):**
- home_hero_title, home_hero_subtitle, home_hero_description
- home_hero_cta_primary, home_hero_cta_secondary
- home_about_title, home_about_description, home_about_cta
- home_courses_title, home_courses_description
- home_meditation_title, home_meditation_subtitle
- home_benefits_title, home_benefits_mental, home_benefits_physical, home_benefits_spiritual
- home_cta_title, home_cta_button

**Танилцуулга хуудас (3):**
- about_title, about_subtitle, about_description

**Бясалгалын төрлүүд (12):**
- gotopa_title, gotopa_subtitle
- guru_title, guru_subtitle
- center_title, center_subtitle
- beginner_title, beginner_subtitle
- intermediate_title, intermediate_subtitle
- advanced_title, advanced_subtitle
- vip_title, vip_subtitle

**Сургалтууд (2):**
- courses_title, courses_description

**Бүтээгдэхүүн (4):**
- products_title, products_subtitle
- books_title, books_subtitle

**Аялал (2):**
- travel_title, travel_subtitle

**Холбоо барих (5):**
- contact_title, contact_phone, contact_email, center_address

**Мэдээ (2):**
- news_title, news_subtitle

## Хэрэглэгчийн эрх тохируулга

### Content Editor эрх олгох:

**Зааварчилгаа:** [FIX_BAYASAA_USER.md](FIX_BAYASAA_USER.md)

```bash
# 1. Management command ашиглах:
python manage.py fix_bayasaa_user

# 2. Django admin дээр гараар:
# - Users → bayasaa68@gmail.com сонгох
# - Staff status: ✓ (заавал)
# - Groups → Content Editor сонгох
# - Save
```

### Эрх шалгах:

```python
# Django shell:
python manage.py shell

from django.contrib.auth.models import User
user = User.objects.get(email='bayasaa68@gmail.com')
print(f"is_staff: {user.is_staff}")  # True байх ёстой
print(f"Groups: {user.groups.all()}")  # Content Editor
print(f"Permissions: {user.has_perm('main.can_edit_content')}")  # True
```

## Inline Editing хэрхэн ажиллах вэ?

### 1. Нэвтрэх:
- Email: `bayasaa68@gmail.com`
- Password: (таны тохируулсан нууц үг)

### 2. Хуудсанд засах товчлуур харагдана:
```
[Гарчиг текст]  [✎ Засах]
```

### 3. "Засах" дарахад modal нээгдэнэ:
- Rich text editor (CKEditor)
- Хадгалах / Цуцлах товчлуур

### 4. Хадгалахад:
- AJAX POST `/api/update-content/`
- Database автоматаар шинэчлэгдэнэ
- Хуудас refresh хийхгүйгээр шинэчлэгдэнэ

## Техникийн дэлгэрэнгүй

### Context Processor:
**Файл:** `main/context_processors.py`

```python
def page_content_processor(request):
    """Бүх template-д page_contents болон can_edit_content нэмнэ"""
    from main.models import PageContent
    
    page_contents = {}
    for content in PageContent.objects.filter(is_active=True):
        page_contents[content.key] = content.content
    
    can_edit_content = (
        request.user.is_authenticated and 
        request.user.is_staff and 
        request.user.has_perm('main.can_edit_content')
    )
    
    return {
        'page_contents': page_contents,
        'can_edit_content': can_edit_content
    }
```

### Template Tag:
**Файл:** `main/templatetags/content_tags.py`

```python
from django import template
register = template.Library()

@register.simple_tag(takes_context=True)
def editable(context, key, default=''):
    """Editable контент wrapper"""
    request = context['request']
    page_contents = context.get('page_contents', {})
    can_edit = context.get('can_edit_content', False)
    
    content = page_contents.get(key, default)
    
    if can_edit:
        return format_html(
            '<span class="editable-content" data-key="{}">'
            '{}<button class="edit-btn" onclick="editContent(\'{}\')">✎ Засах</button>'
            '</span>',
            key, content, key
        )
    return content
```

### AJAX Endpoint:
**Файл:** `main/views.py`

```python
@login_required
def update_page_content(request):
    """AJAX endpoint контент шинэчлэхэд"""
    if not request.user.has_perm('main.can_edit_content'):
        return JsonResponse({'success': False, 'error': 'Эрхгүй'}, status=403)
    
    key = request.POST.get('key')
    content = request.POST.get('content')
    
    page_content, created = PageContent.objects.get_or_create(
        key=key,
        defaults={'content': content, 'updated_by': request.user}
    )
    
    if not created:
        page_content.content = content
        page_content.updated_by = request.user
        page_content.save()
    
    return JsonResponse({'success': True})
```

### JavaScript:
**Файл:** `main/templates/main/base.html`

```javascript
function editContent(key) {
    const content = document.querySelector(`[data-key="${key}"]`).innerHTML;
    document.getElementById('contentKey').value = key;
    document.getElementById('contentEditor').value = content.replace(/<button.*<\/button>/g, '').trim();
    document.getElementById('editModal').classList.remove('hidden');
}

function saveContent() {
    const key = document.getElementById('contentKey').value;
    const content = document.getElementById('contentEditor').value;
    
    fetch('/api/update-content/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: `key=${encodeURIComponent(key)}&content=${encodeURIComponent(content)}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        }
    });
}
```

## Шинэ хуудас нэмэх үед:

### 1. Template үүсгэх:
```django
{% extends 'main/base.html' %}
{% load static %}
{% load content_tags %}  <!-- Энийг нэмэх -->

{% block content %}
<h1>{% editable 'new_page_title' 'Default Title' %}</h1>
<p>{% editable 'new_page_description' 'Default Description' %}</p>
{% endblock %}
```

### 2. Database-д анхдагч контент нэмэх:
```python
# Django shell эсвэл management command:
from main.models import PageContent

PageContent.objects.create(
    key='new_page_title',
    title='New Page Title',
    content='Default Title',
    page='new_page',
    is_active=True
)
```

### 3. URL болон view нэмэх:
```python
# main/urls.py
path('new-page/', views.new_page, name='new_page'),

# main/views.py
def new_page(request):
    return render(request, 'main/new_page.html')
```

## Асуудал шийдвэрлэх

### Засах товчлуур харагдахгүй байна:
1. Хэрэглэгч **is_staff=True** эсэхийг шалгах
2. **Content Editor** group-д орсон эсэхийг шалгах
3. Browser console-д JavaScript алдаа байгаа эсэхийг шалгах

### Хадгалагдахгүй байна:
1. CSRF token зөв байгаа эсэхийг шалгах
2. Browser Network tab-д 403/500 алдаа байгаа эсэхийг шалгах
3. Django logs шалгах

### Template tag ажиллахгүй байна:
1. `{% load content_tags %}` нэмсэн эсэхийг шалгах
2. Server restart хийх: `python manage.py runserver`
3. Template syntax алдаа шалгах

## Хүснэгт: Шинэчилсэн файлууд

| Файл | Статус | Editable Tags | Database Keys |
|------|---------|---------------|---------------|
| about.html | ✅ Шинэчилсэн | 3 | about_title, about_subtitle, about_description |
| contact.html | ✅ Шинэчилсэн | 4 | contact_title, contact_phone, contact_email, center_address |
| courses.html | ✅ Шинэчилсэн | 2 | courses_title, courses_description |
| beginner_meditation.html | ✅ Шинэчилсэн | 2 | beginner_title, beginner_subtitle |
| products.html | ✅ Шинэчилсэн | 2 | products_title, products_subtitle |
| books.html | ✅ Шинэчилсэн | 2 | books_title, books_subtitle |
| travel.html | ✅ Шинэчилсэн | 2 | travel_title, travel_subtitle |
| gotopa_meditation.html | ✅ Шинэчилсэн | 2 | gotopa_title, gotopa_subtitle |
| guru_gotopa.html | ✅ Шинэчилсэн | 2 | guru_title, guru_subtitle |
| meditation_center.html | ✅ Шинэчилсэн | 2 | center_title, center_subtitle |
| news.html | ✅ Шинэчилсэн | 2 | news_title, news_subtitle |
| vip_meditation.html | ✅ Шинэчилсэн | 2 | vip_title, vip_subtitle |
| home.html | ✅ Шинэчилсэн | 18 | home_* keys (18 төрөл) |

## Дараагийн алхмууд

### Хэрэв intermediate_meditation.html болон advanced_meditation.html үүсгэвэл:

1. Template үүсгэх:
```django
{% extends 'main/base.html' %}
{% load static %}
{% load content_tags %}

{% block content %}
<h1>{% editable 'intermediate_title' 'Дунд шатны бясалгал' %}</h1>
<p>{% editable 'intermediate_subtitle' 'Subtitle' %}</p>
{% endblock %}
```

2. Database контент нэмэх:
```bash
python manage.py shell
```
```python
from main.models import PageContent

PageContent.objects.create(
    key='intermediate_title',
    title='Intermediate Meditation Title',
    content='Дунд шатны бясалгал',
    page='intermediate_meditation',
    is_active=True
)
```

## Хувилбарын мэдээлэл

- **Үүсгэсэн:** 2025-01-04
- **Django:** 6.0
- **Python:** 3.13
- **django-ckeditor:** 6.7.1
- **Төлөв:** ✅ Бэлэн ашиглахад

---

**Санамж:** Энэ систем одоо БҮХ хэрэглэгчид харагдаж байгаа хуудсууд дээр контент засах боломжийг олгож байна. Content Editor эрхтэй хэрэглэгчид шууд хуудсан дээр засах товчлуур харагдана!
