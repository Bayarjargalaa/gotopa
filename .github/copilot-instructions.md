# Copilot Instructions - Готопа Бясалгалын Төв

## Project Overview
**Готопа бясалгалын төв** - Django-based meditation center management platform with multi-role authentication, course enrollment system, and custom phone/email login.

**Status**: Active development - Django 5.0+ + Tailwind CSS (CDN) + CKEditor  
**Language**: Python 3.13, All UI/content in Mongolian (locale: `mn`, timezone: `Asia/Ulaanbaatar`)  
**Database**: SQLite (`db.sqlite3`)  
**Dependencies**: Django 5.0+, Pillow 10.0+, django-tailwind 3.8+ (see [requirements.txt](requirements.txt))  
**Note**: CKEditor installed but NOT in requirements.txt - install manually: `pip install django-ckeditor`

## Core Architecture

### Role-Based Access System
The platform implements a hierarchical role system via [main/models.py](main/models.py) `UserRole` enum:
- **PRESIDENT/DIRECTOR/MANAGER/ACCOUNTANT**: Admin roles - full dashboard access, student management, course CRUD, accounting access
- **TEACHER_BEGINNER/INTERMEDIATE/ADVANCED**: Teaching roles - course-specific access, attendance tracking
- **STUDENT**: Default role - view courses, enrollment, personal dashboard

**Key Pattern**: All role checks use `UserProfile.is_teacher`, `UserProfile.is_admin`, and `UserProfile.is_accountant` properties (see [main/models.py](main/models.py) lines 72-99).

### Custom Authentication Backend
[main/backends.py](main/backends.py) implements `PhoneOrEmailBackend` for triple authentication:
1. Username (e.g., `president`, `student_88001234`)
2. Email address (e.g., `user@gotopa.mn`)
3. Phone number (last 8 digits, e.g., `99001234`)

**Critical**: [gotopa_project/settings.py](gotopa_project/settings.py) lists `PhoneOrEmailBackend` FIRST in `AUTHENTICATION_BACKENDS` to prioritize phone/email login.

### Data Model Relationships
```
User (Django built-in)
  ├─ UserProfile (1:1) - role, mongolian_name, phone, enrollment_date
  │   ├─ Course (FK teacher) - level, duration, price, max_students
  │   │   └─ Enrollment (FK student, FK course) - status, payment tracking
  │   │       └─ Attendance (FK enrollment) - date, is_present
  │   └─ BankTransaction (FK income_student) - student payment tracking
  ├─ PageContent (FK updated_by) - key, content (RichTextField), page
  └─ AccountingEntry (FK created_by) - journal entries
      ├─ ChartOfAccounts (FK debit/credit) - account balances
      └─ BankTransaction (FK accounting_entry) - bank reconciliation

Accounting Flow:
  BankTransaction → classify → AccountingEntry → updates ChartOfAccounts balances
  PaymentAllocation: splits one BankTransaction into multiple student/course/month allocations
```

**Pattern**: Always access user's Mongolian name via `user.profile.mongolian_name` with fallback to `user.get_full_name()` or `user.username` (see [main/views.py](main/views.py) lines 28-33).

### Accounting & Finance Module
The platform includes a **double-entry bookkeeping system** for financial management:

**Core Models** (see [main/models.py](main/models.py) lines 308-970):
- **ChartOfAccounts**: Account hierarchy (code, type: ASSET/LIABILITY/EQUITY/INCOME/EXPENSE/COST)
  - Properties: `.balance` (calculated from opening_balance + debits - credits)
  - Auto-updates via `AccountingEntry` save/delete signals
- **AccountingEntry**: Journal entries with debit/credit accounts
  - Auto-generates entry numbers per day
  - Updates account balances on save/delete
  - Links to `BankTransaction` for reconciliation
- **BankTransaction**: Raw bank statement imports (Khan Bank, Golomt Bank)
  - Fields: `income_amount`, `expense_amount`, `offset_account`, `is_processed`
  - Payment classification: `income_type`, `income_student`, `income_month`, `income_year`
  - Color coding: `payment_color` for visual tracking
- **PaymentAllocation**: Splits one bank transaction into multiple student payments
  - One-to-many relationship with BankTransaction
  - Tracks student, course, month, year per allocation

**Critical Workflow** (see [main/views.py](main/views.py) finance views):
1. Import bank statement Excel → `BankTransaction` (via [main/import_bank_transactions.py](main/import_bank_transactions.py))
2. Classify income → set `offset_account`, `income_type`, `income_student`
3. Link to journal → create `AccountingEntry` (debit bank_account, credit offset_account)
4. Auto-update `ChartOfAccounts` balances via model signals

**Bank Import Formats** (see [main/import_bank_transactions.py](main/import_bank_transactions.py)):
- **Khan Bank**: Дебит гүйлгээ, Кредит гүйлгээ columns
- **Golomt Bank**: Орлого, Зарлага columns
- Auto-detects header row, handles Mongolian date formats
- Command: `python manage.py import_bank_transactions_excel <file.xlsx> <bank_account_code>`

### Content Management System (CMS)
The platform includes a database-driven CMS for editing text without code changes:
- **Model**: `PageContent` with CKEditor `RichTextField` for rich text editing
- **Access**: Requires `is_staff=True` + `Content Editor` group OR superuser
- **Template tag**: `{% editable 'key' "default" %}` auto-wraps content with edit buttons for authorized users
- **Context processor**: `page_content_processor` injects `page_contents` dict and `can_edit_content` into all templates

**Permission pattern** (see [main/models.py](main/models.py) lines 269-277):
```python
# Custom permission in PageContent.Meta
permissions = [('can_edit_content', 'Хуудасны агуулга засах эрхтэй')]
```

## Development Workflow

### Essential Commands (Windows PowerShell)
```powershell
# Start server
python manage.py runserver
# Access: http://127.0.0.1:8000 or http://202.179.22.189:8000 (allowed host)

# Database migrations (after model changes)
python manage.py makemigrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Change password for existing users
python manage.py changepassword president  # or any username

# Collect static files (before deployment)
python manage.py collectstatic --noinput

# Content Management System commands
python manage.py init_page_content        # Initialize default page content
python manage.py setup_content_editor     # Create Content Editor group with permissions
python manage.py create_content_editor_user  # Create example content editor user

# Accounting/Finance commands
python manage.py init_chart_of_accounts   # Initialize Mongolian chart of accounts
python manage.py init_cash_flow_indicators  # Initialize cash flow statement indicators
python manage.py import_bank_transactions_excel <file.xlsx> <bank_account_code>
python manage.py import_counterparties_excel <file.xlsx>

# Data integrity utilities (root-level scripts)
python check_bank_transactions.py         # View transaction stats, unprocessed count
python check_chart_of_accounts.py         # Verify account balances
python check_journal.py                   # Audit journal entries
python fix_orphaned_transactions.py       # Clean up orphaned accounting entries
python auto_fix_wrong_offset.py           # Auto-correct mismatched offset accounts
```

### Testing Authentication
Test users documented in [LOGIN_GUIDE.md](LOGIN_GUIDE.md):
- President: `99001234` / `president@gotopa.mn` / `president` (password: `gotopa2025`)
- Teacher: `99001236` / `teacher1@gotopa.mn` / `teacher_beginner` (password: `gotopa2025`)
- Student: `88001234` (after Excel import via [main/import_excel.py](main/import_excel.py))

### Debugging Tips
```powershell
# Access Django shell for manual testing
python manage.py shell

# Example: Test authentication backend
from django.contrib.auth import authenticate
user = authenticate(username='99001234', password='gotopa2025')
print(user)  # Should return User object

# Check user profile
from main.models import UserProfile
profile = UserProfile.objects.get(user__username='president')
print(f"Role: {profile.role}, Is Admin: {profile.is_admin}")

# Verify accounting balances
from main.models import ChartOfAccounts
bank_account = ChartOfAccounts.objects.get(code='1101')
print(f"Balance: {bank_account.balance:,.0f}₮")
print(f"Debits: {bank_account.debit_balance:,.0f}₮, Credits: {bank_account.credit_balance:,.0f}₮")

# Check unprocessed bank transactions
from main.models import BankTransaction
unprocessed = BankTransaction.objects.filter(is_processed=False).count()
print(f"Unprocessed transactions: {unprocessed}")
```

**Utility Scripts**: Root-level `check_*.py` and `fix_*.py` scripts (e.g., `check_bank_transactions.py`, `auto_fix_wrong_offset.py`) are standalone tools for data integrity - run them directly with `python <script>.py` (they auto-configure Django environment).

## Code Conventions

### Design System - PRIMARY COLOR PURPLE (#b5245b)
**CRITICAL RULE**: All primary actions, links, buttons MUST use purple (#b5245b), NOT blue/other colors.

Tailwind classes in [main/templates/main/base.html](main/templates/main/base.html):
```html
<!-- Primary buttons -->
<a class="bg-primary text-white hover:bg-opacity-90">Нэвтрэх</a>

<!-- Hover states -->
<a class="text-secondary hover:text-primary">Link</a>

<!-- Tailwind config defines custom colors -->
<script>
  tailwind.config = {
    theme: { extend: { colors: {
      primary: '#b5245b',    // Purple (ягаан)
      secondary: '#222631',   // Dark gray (text)
      light: '#f8f9fa'        // Light gray (background)
    }}}
  }
</script>
```

### Template Inheritance Pattern
All pages extend [main/templates/main/base.html](main/templates/main/base.html):
```django
{% extends 'main/base.html' %}
{% load static %}
{% load content_tags %}  {# Load custom template tags for CMS #}

{% block title %}Page Title - Готопа{% endblock %}

{% block content %}
  <h1>{% editable 'page_hero_title' "Default Title" %}</h1>
  <!-- Editable content auto-renders with edit buttons for authorized users -->
{% endblock %}
```

**Navigation**: Header dropdowns use `.dropdown-wrapper`, `.dropdown-trigger`, `.dropdown-menu` classes with JavaScript toggle (see [base.html](main/templates/main/base.html) lines 26-59).

**CMS Template Tag**: `{% editable 'key' "default" %}` from [main/templatetags/content_tags.py](main/templatetags/content_tags.py):
- Retrieves content from `page_contents` context (provided by context processor)
- Wraps content in editable wrapper with SVG edit button if `can_edit_content=True`
- Falls back to default value if key not found
- Returns safe HTML (uses `mark_safe`)

### URL Naming Convention
- Namespace: `main` (defined in [main/urls.py](main/urls.py) line 3: `app_name = 'main'`)
- URL names: snake_case (e.g., `beginner_meditation`, `course_list`, `student_list`)
- Usage: Always `{% url 'main:home' %}`, never hardcoded paths

### Model Field Patterns
**Phone validation** (see [main/models.py](main/models.py) lines 25-29):
```python
phone_regex = RegexValidator(
    regex=r'^\+?976?\d{8,}$',
    message="Утасны дугаар +976XXXXXXXX форматтай байх ёстой"
)
phone = models.CharField(validators=[phone_regex], max_length=20)
```

**Verbose names**: All models use Mongolian `verbose_name` and `verbose_name_plural` for admin interface.

## Integration Points

### Admin Customization
[main/admin.py](main/admin.py) extends Django User admin with inline UserProfile:
- List filters by role, active status, city
- Search by Mongolian name, username, email, phone
- Inline editing prevents orphaned User records

### Student Import System
[main/import_excel.py](main/import_excel.py) processes Excel files with columns:
- Нэр (Name), Утас (Phone), Имэйл (Email), Хаяг (Address)
- Auto-generates username: `student_{phone_last_8_digits}`
- Default password: last 8 digits of phone
- Handles duplicate phone/email validation

**Usage**: Call from Django shell or create management command.

### Static Files Configuration
```python
# Development: Tailwind CSS via CDN in base.html
# Production TODO: Build Tailwind locally (tailwind.config.js exists but not integrated)

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']  # Source files
STATIC_ROOT = BASE_DIR / 'staticfiles'     # Collected files

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'            # User uploads (profile photos)

# CKEditor Configuration (settings.py lines 140-157)
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
    'advanced': {
        'toolbar': 'Full',
        'height': 400,
        'width': '100%',
    },
}
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_RESTRICT_BY_USER = True
CKEDITOR_BROWSE_SHOW_DIRS = True
```

### Context Processors
[main/context_processors.py](main/context_processors.py) `page_content_processor` runs on every request:
- Injects `page_contents` dict (all active PageContent.key → PageContent.content)
- Injects `can_edit_content` boolean (staff user + superuser OR Content Editor group)

## Key Files Reference
- [CONTENT_MANAGEMENT_README.md](CONTENT_MANAGEMENT_README.md) - CMS overview, permissions, editing workflow
- [CONTENT_EDITOR_PERMISSION.md](CONTENT_EDITOR_PERMISSION.md) - How to grant content editing permissions
- [CONTENT_EDITING_GUIDE.md](CONTENT_EDITING_GUIDE.md) - Step-by-step guide for editing page content

### Core Configuration
- [gotopa_project/settings.py](gotopa_project/settings.py) - Custom auth backend, Mongolia locale, allowed hosts (`202.179.22.189`)
- [main/urls.py](main/urls.py) - All URL patterns with `app_name = 'main'` namespace
- [main/models.py](main/models.py) - UserProfile, Course, Enrollment, Attendance, ChartOfAccounts, AccountingEntry, BankTransaction models
- [requirements.txt](requirements.txt) - Django 5.0+, Pillow 10.0+, django-tailwind 3.8+

### Authentication Flow
- [main/backends.py](main/backends.py) - `PhoneOrEmailBackend` implementation
- [main/views.py](main/views.py) - `user_login()`, `register()`, `dashboard()` views
- [main/templates/main/login.html](main/templates/main/login.html) - Login form with phone/email support

### Accounting & Finance
- [main/import_bank_transactions.py](main/import_bank_transactions.py) - Excel import for Khan/Golomt bank statements
- [main/views.py](main/views.py) - Finance dashboard, journal, chart of accounts views
- [main/views_payments.py](main/views_payments.py) - Student payment tracking by month/year/course
- Root-level utility scripts: `check_*.py`, `fix_*.py` for data integrity

### UI Components
- [main/templates/main/base.html](main/templates/main/base.html) - Header, footer, mobile menu, Tailwind config
- [static/css/custom.css](static/css/custom.css) - Custom styles (minimal, Tailwind-first approach)

### Documentation
- [LOGIN_GUIDE.md](LOGIN_GUIDE.md) - Role-based access guide, test credentials
- [PHONE_EMAIL_LOGIN.md](PHONE_EMAIL_LOGIN.md) - Authentication system technical details
- [USER_MANAGEMENT_README.md](USER_MANAGEMENT_README.md) - Student/teacher management workflows

## Common Patterns

### View Authentication Check
```python
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect

@login_required
def dashboard(request):
    profile = request.user.profile
    if profile.is_admin:
        # Admin dashboard - full access to student/course management
        students = UserProfile.objects.filter(role=UserRole.STUDENT)
        courses = Course.objects.all()
    elif profile.is_teacher:
        # Teacher dashboard - only courses they teach
        courses = Course.objects.filter(teacher=profile)
    else:
        # Student dashboard - only their enrollments
        enrollments = Enrollment.objects.filter(student=profile)
    
    return render(request, 'main/dashboard.html', context)

# Restrict access to admin-only views
@login_required
def course_create(request):
    if not request.user.profile.is_admin:
        messages.error(request, 'Зөвхөн админ хэрэглэгч хичээл үүсгэх эрхтэй.')
        return redirect('main:dashboard')
    # Create course logic...
```

### Display User Name in Templates
```django
{{ user.profile.mongolian_name|default:user.username }}
```

### Course Enrollment Count
```python
# Model property (main/models.py lines 134-141)
course.enrolled_count  # Active enrollments
### CMS Content Access Pattern
```python
# In views - context processor auto-injects page_contents
def home(request):
    # No need to manually query PageContent
    return render(request, 'main/home.html')  # page_contents already available

# In templates - use editable tag
{% load content_tags %}
<h1>{% editable 'home_hero_title' "Готопа бясалгалын төв" %}</h1>

# Grant editing permission
from django.contrib.auth.models import User, Group
user = User.objects.get(username='editor')
user.is_staff = True
user.groups.add(Group.objects.get(name='Content Editor'))
user.save()
```

course.available_slots  # max_students - enrolled_count
```

---

**REMEMBER**: This is a Mongolian language platform. All user-facing text, messages, error strings MUST be in Mongolian. Purple (#b5245b) is the brand color - do not use blue for primary actions!
