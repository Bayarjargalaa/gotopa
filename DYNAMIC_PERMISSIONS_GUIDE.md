# Эрхийн бүлэгт эрх нэмэх/хасахад динамик ажиллалт

## ✅ Баталгаажсан үр дүн:

### 1️⃣ Эхний төлөв (MANAGER роль)
- Хувийн (2 зүйл)
- Бараа материал (6 зүйл)
- Сургалт (5 зүйл)

### 2️⃣ "Менежер" бүлэгт "Can view Дансны төлөвлөгөө" эрх нэмсний дараа:
```
✅ Санхүү цэс ГАРЧ ИРЛЭЭ!
   📂 Санхүү (1 зүйл)
      • Дансны төлөвлөгөө
```

### 3️⃣ Тэр эрхийг хассаны дараа:
```
✅ Санхүү цэс АЛГА БОЛСОН!
```

## 🔧 Яаж ажиллаж байна:

### Django Permission System:
```python
# Admin panel дээр:
1. Groups → "Менежер" → Permissions
2. "main | Дансны төлөвлөгөө | Can view Дансны төлөвлөгөө" ✓ чагтлах
3. Save

# Хэрэглэгч page refresh хийх (F5)
# → Sidebar-д "Санхүү → Дансны төлөвлөгөө" гарч ирнэ

# Permission хасах:
1. Groups → "Менежер" → Permissions
2. "Can view Дансны төлөвлөгөө" чагт тайлах
3. Save

# Хэрэглэгч page refresh хийх (F5)
# → Sidebar-аас "Санхүү" цэс алга болно
```

### Code Level:
```python
# main/menu_config.py (мөр 44-48)
{
    'label': 'Дансны төлөвлөгөө',
    'url_name': 'main:chart_of_accounts_list',
    'icon': 'fas fa-list-alt',
    'permissions': ['is_admin', 'is_accountant', 'perm:main.view_chartofaccounts'],
    #                                              ^^^ ЭНЭ НЬ ДИНАМИКААР ШАЛГАГДАНА
},

# main/menu_config.py (мөр 313-316)
if permission.startswith('perm:'):
    perm_name = permission.split(':')[1]
    if user.has_perm(perm_name):  # 👈 Database query - бүлгийн эрх автоматаар шалгагдана
        return True
```

### Django's user.has_perm() автоматаар:
1. Хэрэглэгчийн бүлгүүдийг database-ээс татна
2. Тэр бүлгүүдийн эрхүүдийг шалгана
3. Эрх олдвол True буцаана
4. **Session шинэчлэх хэрэггүй!** (зөвхөн page refresh)

## 📋 Практик жишээ:

### Менежерт Санхүү модулийн бүх эрх өгөх:

```bash
# Admin panel дээр:
Groups → Менежер → Permissions → Select:

Accounting:
✓ Can add Журналын бичилт
✓ Can change Журналын бичилт  
✓ Can delete Журналын бичилт
✓ Can view Журналын бичилт

Chart of Accounts:
✓ Can add Дансны төлөвлөгөө
✓ Can change Дансны төлөвлөгөө
✓ Can delete Дансны төлөвлөгөө
✓ Can view Дансны төлөвлөгөө

Bank Transaction:
✓ Can add Банкны гүйлгээ
✓ Can change Банкны гүйлгээ
✓ Can delete Банкны гүйлгээ
✓ Can view Банкны гүйлгээ

→ Save
→ Менежер хэрэглэгч page refresh (F5)
→ Санхүү цэсэнд 6 зүйл гарч ирнэ:
   • Санхүүгийн хяналт
   • Журнал
   • Дансны төлөвлөгөө
   • Банкны хуулга оруулах
   • Банкны гүйлгээ
   • Кассын бүртгэл
```

## ⚠️ Онцгой анхаарах зүйл:

### Browser дээр:
- Django-ийн permission cache нь **session-д хадгалагддаггүй**
- Хэрэглэгч page refresh бүрт `user.has_perm()` нь **database-ээс шууд шалгана**
- Logout/Login хэрэггүй - **F5 л хангалттай**

### Алдаа гарч болзошгүй:
Хэрэв permission нэмсэн боловч цэс гарч ирэхгүй бол:
1. ✅ Permission зөв codename шалгах (`view_chartofaccounts` биш `Can view...`)
2. ✅ App label зөв байгааг шалгах (`main.view_chartofaccounts`)
3. ✅ menu_config.py-д `perm:` prefix байгааг шалгах
4. ✅ Section-ийн permission хоосон эсвэл item-үүдийн эрхтэй таарч байгааг шалгах

## 🎯 Дүгнэлт:

✅ **ТИЙМ** - Бүлэгт эрх нэмэх/хасах нь динамикаар ажиллана  
✅ **Page refresh** л хийвэл цэс шууд өөрчлөгдөнө  
✅ **Logout/Login хэрэггүй**  
✅ **Real-time database query**  
✅ **user.has_perm()** нь бүлгийн эрхийг автоматаар шалгана
