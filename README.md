# Готопа Бясалгалын Төв - Web Platform

Готопа бясалгалын төвийн албан ёсны вэб платформ. Django framework дээр бүтээгдсэн, Tailwind CSS ашигласан.

## 🎨 Дизайн

- **Үндсэн өнгө**: Ягаан (#AB334C)
- **Хоёрдогч өнгө**: Хар саарал (#222631)
- **Framework**: Tailwind CSS

## 🚀 Хурдан эхлэл

### Шаардлагатай зүйлс
- Python 3.13+
- Django 6.0+
- Pillow (зураг ажиллуулах)

### Суулгах

```bash
# Dependencies суулгах
pip install -r requirements.txt

# Database бэлдэх
python manage.py migrate

# Static файлууд цуглуулах
python manage.py collectstatic --noinput

# Server ажиллуулах
python manage.py runserver
```

Вэб хөтөч дээр: `http://127.0.0.1:8000`

## 📁 Төслийн бүтэц

```
gotopa/
├── gotopa_project/     # Django тохиргоо
├── main/               # Үндсэн app
│   ├── templates/     # HTML templates
│   ├── views.py       # View functions
│   └── urls.py        # URL patterns
├── static/            # CSS, JS, зургууд
├── media/             # Upload файлууд
└── manage.py
```

## 🎯 Онцлогууд

- ✅ Responsive дизайн (mobile-friendly)
- ✅ Ягаан өнгөтэй брэнд дизайн
- ✅ Монгол хэл дэмжлэг
- ✅ Tailwind CSS utilities
- ✅ SEO-friendly structure

## 🔧 Хөгжүүлэлт

### Admin panel
```bash
# Superuser үүсгэх
python manage.py createsuperuser

# Admin panel: http://127.0.0.1:8000/admin
```

### Static файлууд шинэчлэх
```bash
python manage.py collectstatic
```

## 📝 License

© 2025 Готопа бясалгалын төв. Бүх эрх хуулиар хамгаалагдсан.

## 📞 Холбоо барих

- **Хаяг**: Улаанбаатар, ГрандПлаза, 904 тоот
- **Утас**: (+976) 70110205, 96666895
- **Email**: gotopa@gmail.com
