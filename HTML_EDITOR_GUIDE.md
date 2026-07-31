# 🎨 HTML Засварлах систем - CKEditor

## Тойм

Админ панелд **Rich Text Editor (CKEditor)** суусан. Одоо агуулга засагч:
- ✅ **Bold**, *Italic*, <u>Underline</u> форматчлал
- ✅ Өнгө солих
- ✅ Жагсаалт үүсгэх
- ✅ Link нэмэх
- ✅ HTML код харах/засах

---

## 📝 Хэрхэн ашиглах

### 1. Админ панелаар нэвтрэх

```
URL: http://127.0.0.1:8000/admin/
Username: content_editor (эсвэл бусад Content Editor эрхтэй)
Password: gotopa2025
```

### 2. Хуудасны агуулга засах

1. **"Хуудасны агуулгууд"** цэс сонгох
2. Засах текст сонгох (жишээ: "Нүүр - Hero үндсэн гарчиг")
3. **"Агуулга"** талбар дээр **WYSIWYG editor** харагдана

### 3. Форматчлах

#### Toolbar товчнууд:

| Товч | Үүрэг | Жишээ |
|------|-------|-------|
| **B** | Тод үсэг | **Готопа** |
| *I* | Налуу үсэг | *бясалгал* |
| <u>U</u> | Доогуур зураастай | <u>чухал</u> |
| ~~S~~ | Дундуур нь зураастай | ~~хуучин үг~~ |
| 🎨 | Текст өнгө | <span style="color: red;">Улаан</span> |
| 🖌️ | Дэвсгэр өнгө | <span style="background: yellow;">Шар</span> |
| 1. | Дугаарлагдсан жагсаалт | 1. Эхний<br>2. Хоёрдугаар |
| • | Цэг жагсаалт | • Нэг<br>• Хоёр |
| 🔗 | Холбоос нэмэх | [Готопа](https://gotopa.mn) |
| ⌫ | Форматчлал арилгах | Энгийн текст |
| </> | HTML код харах | Source mode |

---

## 🎯 Жишээ ашиглалт

### Жишээ 1: Онцгой үг тодруулах

**Админд:**
```
Энэ нь **онцгой** мессеж юм
```

**Вэб дээр:**
```html
Энэ нь <strong>онцгой</strong> мессеж юм
```

### Жишээ 2: Өнгөтэй текст

**Toolbar:**
1. Текст сонгох: "Готопа бясалгал"
2. 🎨 Text Color товч дарах
3. Өнгө сонгох (жишээ: ягаан #AB334C)

**Үр дүн:**
```html
<span style="color: #AB334C;">Готопа бясалгал</span>
```

### Жишээ 3: Жагсаалт

**Toolbar:**
1. • Bullet List товч дарах
2. Enter дарж шинэ мөр нэмэх

**Үр дүн:**
```
• Анхан шатны хичээл
• Дунд шатны хичээл
• Дээд шатны хичээл
```

### Жишээ 4: Холбоос нэмэх

**Toolbar:**
1. Текст сонгох: "Дэлгэрэнгүй унших"
2. 🔗 Link товч дарах
3. URL оруулах: `/about/`

**Үр дүн:**
```html
<a href="/about/">Дэлгэрэнгүй унших</a>
```

---

## 🔧 HTML Code засах (Advanced)

### Source Mode

**Ашиглах үед:**
- Өөрийн HTML код бичих
- Нарийн форматчлал хийх
- CSS style нэмэх

**Хэрхэн:**
1. </> **Source** товч дарах
2. HTML код шууд засах
3. Дахин дарж visual mode руу буцах

**Жишээ HTML:**
```html
<p>Энэ нь <strong style="color: #AB334C;">онцгой</strong> текст юм.</p>
<ul>
  <li>Нэг</li>
  <li>Хоёр</li>
</ul>
```

---

## ⚙️ CKEditor тохиргоо

[gotopa_project/settings.py](gotopa_project/settings.py) файлд:

```python
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Bold', 'Italic', 'Underline', 'Strike'],
            ['TextColor', 'BGColor'],
            ['NumberedList', 'BulletedList'],
            ['Link', 'Unlink'],
            ['RemoveFormat', 'Source'],
        ],
        'height': 300,
        'width': '100%',
    },
}
```

### Нэмэлт товч нэмэх:

Хэрэв **зураг**, **хүснэгт**, **видео** гэх мэт нэмэхийг хүсвэл:

```python
'toolbar_Custom': [
    ['Bold', 'Italic', 'Underline'],
    ['Image', 'Table', 'HorizontalRule'],
    ['JustifyLeft', 'JustifyCenter', 'JustifyRight'],
    ['Format', 'Font', 'FontSize'],
]
```

---

## ⚠️ Анхаарах зүйлс

### ✅ Хийх

- Монгол хэл дээр бичих
- Товч, ойлгомжтой текст
- Өнгө ашиглахдаа brand color (#AB334C) сонгох
- HTML validation шалгах

### ❌ Хийхгүй

- JavaScript код оруулахгүй (аюулгүй бус)
- `<script>` tag ашиглахгүй
- Inline style хэт ихээр ашиглахгүй (CSS-д тодорхойлох нь дээр)
- Хэт олон өнгө холих

---

## 🔒 Аюулгүй байдал

### XSS (Cross-Site Scripting) хамгаалалт

Django автоматаар HTML-г цэвэршүүлнэ гэхдээ:

**Зөвшөөрөгдсөн:**
```html
<strong>, <em>, <u>, <a>, <ul>, <li>, <p>, <br>, <span>
```

**Хориотой:**
```html
<script>, <iframe>, <object>, <embed>
```

### Template дээр `|safe` filter

Бид template дээр `|safe` filter ашиглаж байгаа тул:
- ✅ HTML render хийнэ
- ⚠️ Зөвхөн итгэлтэй эх үүсвэрээс агуулга авах

---

## 🐛 Алдааны шийдэл

### CKEditor харагдахгүй байна

```bash
# 1. Collectstatic ажиллуулах
python manage.py collectstatic --noinput

# 2. Migration шалгах
python manage.py migrate

# 3. Cache цэвэрлэх
Ctrl + Shift + R (browser reload)
```

### Форматчлал вэб дээр харагдахгүй

**Шалгах:**
- Template дээр `|safe` filter байгаа эсэх
- HTML код зөв эсэх (Source mode-оор)
- CSS style нь алдаатай биш эсэх

---

## 📊 Өмнөх vs Одоо

| Өмнөх | Одоо (CKEditor) |
|-------|-----------------|
| Энгийн текст | **Bold**, *Italic*, өнгө |
| Форматчлалгүй | Жагсаалт, холбоос |
| HTML мэдлэг шаардлагатай | WYSIWYG editor |
| Code засах | Visual засах |

---

## 🚀 Үргэлжлүүлэх

Хэрэв илүү олон функц хэрэгтэй бол:

1. **Зураг оруулах**: `django-ckeditor` зургийн upload
2. **File upload**: Media library нэмэх
3. **Advanced editor**: TinyMCE, Quill.js сонголтууд

---

**Одоо туршиж үзээрэй:**
1. http://127.0.0.1:8000/admin/ нэвтрэх
2. Хуудасны агуулга засах
3. **Bold**, өнгө, жагсаалт ашиглах
4. Хадгалаад нүүр хуудсаа шалгах!

**Амжилт хүсье!** 🎉
