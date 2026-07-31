"""
View функцүүдэд mongolian_name POST өгөгдлийг last_name, first_name болгон өөрчлөх тайлбар

Засах шаардлагатай view-үүд:
1. student_create (line ~287)
2. student_update (line ~416)  
3. teacher_create (line ~583)
4. teacher_update (line ~688)

Засах зарчим:
- POST.get('mongolian_name') → POST.get('last_name'), POST.get('first_name')
- Validation: "if not mongolian_name" → "if not last_name or not first_name"
- UserProfile.create/update: mongolian_name=... → last_name=..., first_name=...

Гэхдээ эдгээр нь хөгжүүлэгчийн зүгээс гараар засах шаардлагатай, учир нь:
- Бизнес логик өөрчлөх (validation, error messages)
- Database import scripts (import_excel.py) ч засах шаардлагатай
- Register form template (/register/) ч засах шаардлагатай

ОДООГИЙН ТӨЛӨВ:
✅ Model: last_name, first_name талбарууд нэмэгдсэн
✅ Migration: Амжилттай ажиллуулсан
✅ Template display: .mongolian_name → .full_name (бүгд өөрчлөгдсөн)
✅ Form templates (create/update): Овог, нэр тусад нь оруулах хэсгүүд нэмэгдсэн
⚠️  View POST logic: Засах шаардлагатай (student/teacher create/update)
⚠️  Register form: Засах шаардлагатай

ДАРААГИЙН АЛХАМ:
1. View-үүдийн POST logic засах
2. register.html template засах
3. import_excel.py засах (хуучин Excel файлуудтай ажиллахад)
"""
print(__doc__)
