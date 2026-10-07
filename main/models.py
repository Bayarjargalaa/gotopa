from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.db.models.signals import post_save, pre_save
from django.db.models import Sum
from django.dispatch import receiver
from ckeditor.fields import RichTextField

class UserRole(models.TextChoices):
    """Хэрэглэгчийн эрхийн түвшин"""
    PRESIDENT = 'PRESIDENT', 'Тэргүүн'
    DIRECTOR = 'DIRECTOR', 'Захирал'
    MANAGER = 'MANAGER', 'Менежер'
    ACCOUNTANT = 'ACCOUNTANT', 'Нягтлан'
    TEACHER_BEGINNER = 'TEACHER_BEGINNER', 'Анхан шатны багш'
    TEACHER_INTERMEDIATE = 'TEACHER_INTERMEDIATE', 'Дунд шатны багш'
    TEACHER_ADVANCED = 'TEACHER_ADVANCED', 'Дээд шатны багш'
    STUDENT = 'STUDENT', 'Сурагч'


# Django staff эрх автоматаар авах эрхүүд
STAFF_ROLES = [UserRole.PRESIDENT, UserRole.DIRECTOR, UserRole.MANAGER, UserRole.ACCOUNTANT]
TEACHER_ROLES = [UserRole.TEACHER_BEGINNER, UserRole.TEACHER_INTERMEDIATE, UserRole.TEACHER_ADVANCED]


class TeacherLevel(models.Model):
    """Багшийн мэдээлэлд сонгож хадгалах түвшин."""
    name = models.CharField(max_length=100, unique=True, verbose_name='Нэр')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='Код')
    is_active = models.BooleanField(default=True, verbose_name='Идэвхтэй')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Эрэмбэ')

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Багшийн түвшин'
        verbose_name_plural = 'Багшийн түвшнүүд'

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    """Хэрэглэгчийн дэлгэрэнгүй мэдээлэл"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(
        max_length=30,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
        verbose_name='Эрх'
    )
    
    # Хувийн мэдээлэл
    # Хувийн мэдээлэл
    last_name = models.CharField(max_length=100, verbose_name='Овог', blank=True)
    first_name = models.CharField(max_length=100, verbose_name='Нэр', blank=True)
    mongolian_name = models.CharField(max_length=200, verbose_name='Монгол нэр (хуучин)', blank=True, help_text='Овог + Нэр-ээр орлогдлоо')
    phone_regex = RegexValidator(
        regex=r'^\d{8}$',
        message="Утасны дугаар 8 оронтой тоо байх ёстой"
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=8,
        verbose_name='Утас',
        blank=True
    )
    birth_date = models.DateField(verbose_name='Төрсөн өдөр', null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[('M', 'Эрэгтэй'), ('F', 'Эмэгтэй'), ('O', 'Бусад')],
        verbose_name='Хүйс',
        blank=True,
        null=True
    )
    
    # Хаяг
    address = models.TextField(verbose_name='Хаяг', blank=True)
    city = models.CharField(max_length=100, verbose_name='Хот/Аймаг', blank=True)
    district = models.CharField(max_length=100, verbose_name='Дүүрэг/Сум', blank=True)
    
    # Сургалтын мэдээлэл
    enrollment_date = models.DateField(verbose_name='Элссэн огноо', null=True, blank=True)
    is_active_student = models.BooleanField(default=True, verbose_name='Идэвхтэй эсэх')
    
    # Нэмэлт мэдээлэл
    photo = models.ImageField(upload_to='profiles/', verbose_name='Зураг', null=True, blank=True)
    # Багшийн зураг static/images/багшнар/ фолдерт хадгалагдах файлын нэр
    photo_filename = models.CharField(max_length=255, verbose_name='Зургийн файлын нэр', blank=True, default='')
    teacher_display_order = models.PositiveIntegerField(default=9999, verbose_name='Багшийн жагсаалтын дараалал')
    notes = models.TextField(verbose_name='Тэмдэглэл', blank=True)
    
    # Багшийн зааж буй түвшин (олон утга, таслалаар тусгаарлагдсан, жишээ: "TEACHER_BEGINNER,TEACHER_INTERMEDIATE")
    teacher_levels = models.CharField(max_length=150, verbose_name='Зааж буй түвшин', blank=True, default='')

    # Ажил мэргэжлийн мэдээлэл
    profession = models.CharField(max_length=200, verbose_name='Мэргэжил', blank=True)
    education = models.CharField(max_length=200, verbose_name='Боловсрол', blank=True)
    current_job = models.CharField(max_length=200, verbose_name='Одоо эрхэлж буй ажил', blank=True)
    facebook_name = models.CharField(max_length=200, verbose_name='Facebook нэр', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Үүсгэсэн огноо')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Шинэчилсэн огноо')
    
    class Meta:
        verbose_name = 'Хэрэглэгчийн мэдээлэл'
        verbose_name_plural = 'Хэрэглэгчдийн мэдээлэл'
        ordering = ['-created_at']
    
    @property
    def full_name(self):
        """Овог нэр бүтэн"""
        if self.last_name and self.first_name:
            return f"{self.last_name} {self.first_name}"
        elif self.mongolian_name:
            return self.mongolian_name  # Хуучин формат
        else:
            return self.user.get_full_name() or self.user.username

    @property
    def name_first_display(self):
        """Нэр эхэнд, овог ард нь (жишээ: Бат Дорж)"""
        if self.first_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.full_name

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"
    
    @property
    def is_teacher(self):
        """Багш эсэхийг шалгах"""
        return self.role in [
            UserRole.TEACHER_BEGINNER,
            UserRole.TEACHER_INTERMEDIATE,
            UserRole.TEACHER_ADVANCED
        ]

    def get_teacher_levels_list(self):
        """Зааж буй түвшингүүдийн жагсаалт буцаана"""
        if not self.teacher_levels:
            return [self.role] if self.is_teacher else []
        return [lvl.strip() for lvl in self.teacher_levels.split(',') if lvl.strip()]

    def get_teacher_level_names(self):
        """Сонгосон багшийн түвшнүүдийн нэрийг буцаана."""
        level_slugs = self.get_teacher_levels_list()
        names = dict(TeacherLevel.objects.filter(slug__in=level_slugs).values_list('slug', 'name'))
        return [names[slug] for slug in level_slugs if slug in names]
    
    @property
    def is_admin(self):
        """Админ эрхтэй эсэхийг шалгах - Бүх модуль удирдах эрх"""
        return self.role in [
            UserRole.PRESIDENT,
            UserRole.DIRECTOR,
            # MANAGER хасагдсан - зөвхөн зөвшөөрсөн эрхтэй
        ]
    
    @property
    def is_accountant(self):
        """Нягтлан бодогч эсэхийг шалгах - Зөвхөн санхүүгийн модуль"""
        return self.role == UserRole.ACCOUNTANT
    
    @property
    def is_only_accountant(self):
        """Зөвхөн нягтлан бодогч эрхтэй эсэхийг шалгах (менежер биш) - Устгагдсан, is_accountant ашиглах"""
        return self.role == UserRole.ACCOUNTANT
    
    @property
    def is_manager(self):
        """Менежер эсэхийг шалгах - Зөвшөөрсөн модулиудын эрх"""
        return self.role == UserRole.MANAGER
    
    @property
    def enrolled_courses_count(self):
        """Элссэн сургалтын тоо"""
        return self.enrollments.filter(is_active=True).count()


class Course(models.Model):
    """Сургалтын хичээл"""
    LEVEL_CHOICES = [
        ('BEGINNER_1', '1'),
        ('BEGINNER_2', '2'),
        ('INTERMEDIATE', '3'),
        ('ADVANCED', '4'),
        ('VIP', 'VIP'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Нэр')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, verbose_name='Түвшин')
    description = models.TextField(verbose_name='Тайлбар', blank=True)
    duration_weeks = models.IntegerField(verbose_name='Үргэлжлэх хугацаа (долоо хоног)')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Үнэ (₮)')
    monthly_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name='Сарын төлбөр (₮)',
        help_text='Сурагчийн нэг сарын төлбөр — "Сурагчдын төлбөр" хуудсанд дутуу/бүрэн төлсөнийг тодорхойлно. 0 бол шалгахгүй.'
    )
    
    teacher = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role__in': [
            UserRole.TEACHER_BEGINNER,
            UserRole.TEACHER_INTERMEDIATE,
            UserRole.TEACHER_ADVANCED
        ]},
        related_name='courses_teaching',
        verbose_name='Багш'
    )
    
    start_date = models.DateField(verbose_name='Эхлэх өдөр')
    end_date = models.DateField(verbose_name='Дуусах өдөр')
    schedule = models.CharField(max_length=200, verbose_name='Хуваарь', blank=True, default='')
    max_students = models.IntegerField(default=30, verbose_name='Дээд хязгаар')
    
    is_active = models.BooleanField(default=True, verbose_name='Идэвхтэй')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Сургалт'
        verbose_name_plural = 'Сургалтууд'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"
    
    @property
    def enrolled_count(self):
        """Элссэн сурагчдын тоо"""
        return self.enrollments.filter(is_active=True).count()
    
    @property
    def approved_count(self):
        """Идэвхтэй бөгөөд баталсан төлөвтэй сурагчдын тоо"""
        return self.enrollments.filter(is_active=True, status='APPROVED').count()
    
    @property
    def available_slots(self):
        """Үлдсэн суудал"""
        return self.max_students - self.enrolled_count


class Enrollment(models.Model):
    """Сурагчийн бүртгэл"""
    STATUS_CHOICES = [
        ('PENDING', 'Хүлээгдэж буй'),
        ('APPROVED', 'Баталсан'),
        ('COMPLETED', 'Төгссөн'),
        ('CANCELLED', 'Цуцалсан'),
    ]
    
    student = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        limit_choices_to={'role': UserRole.STUDENT},
        related_name='enrollments',
        verbose_name='Сурагч'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name='Сургалт'
    )
    
    enrolled_date = models.DateField(auto_now_add=True, verbose_name='Бүртгүүлсэн өдөр')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name='Төлөв'
    )
    
    payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Төлсөн дүн (₮)',
        default=0
    )
    payment_date = models.DateField(verbose_name='Төлсөн өдөр', null=True, blank=True)
    is_paid = models.BooleanField(default=False, verbose_name='Төлбөр төлсөн')
    
    certificate_issued = models.BooleanField(default=False, verbose_name='Гэрчилгээ олгосон')
    certificate_date = models.DateField(verbose_name='Гэрчилгээ олгосон өдөр', null=True, blank=True)
    
    is_active = models.BooleanField(default=True, verbose_name='Идэвхтэй')
    notes = models.TextField(verbose_name='Тэмдэглэл', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Бүртгэл'
        verbose_name_plural = 'Бүртгэлүүд'
        ordering = ['-enrolled_date']
        unique_together = ['student', 'course']
    
    def __str__(self):
        return f"{self.student.mongolian_name} - {self.course.name}"


class Attendance(models.Model):
    """Ирц"""
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name='Бүртгэл'
    )
    date = models.DateField(verbose_name='Огноо')
    present = models.BooleanField(default=True, verbose_name='Ирсэн')
    notes = models.TextField(verbose_name='Тэмдэглэл', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Ирц'
        verbose_name_plural = 'Ирцүүд'
        ordering = ['-date']
        unique_together = ['enrollment', 'date']
    
    def __str__(self):
        status = 'Ирсэн' if self.present else 'Тасалсан'
        return f"{self.enrollment.student.mongolian_name} - {self.date} ({status})"


class AttendanceWeekdayTemplate(models.Model):
    """Ирцийн 7 хоногийн гаригийн загвар (анги тус бүр)"""
    course = models.OneToOneField(
        Course,
        on_delete=models.CASCADE,
        related_name='attendance_weekday_template',
        verbose_name='Сургалт'
    )
    # Monday=0 ... Sunday=6 утгуудыг таслалаар тусгаарлан хадгална (жишээ: 0,2,4)
    weekdays = models.CharField(max_length=20, verbose_name='Гаригууд')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ирцийн гаригийн загвар'
        verbose_name_plural = 'Ирцийн гаригийн загварууд'

    def __str__(self):
        return f"{self.course.name} - {self.weekdays_display}"

    def get_weekday_numbers(self):
        numbers = []
        for item in (self.weekdays or '').split(','):
            value = item.strip()
            if not value.isdigit():
                continue
            day = int(value)
            if 0 <= day <= 6:
                numbers.append(day)
        return sorted(set(numbers))

    def set_weekday_numbers(self, weekday_numbers):
        cleaned = sorted({int(day) for day in weekday_numbers if 0 <= int(day) <= 6})
        self.weekdays = ','.join(str(day) for day in cleaned)

    @property
    def weekdays_display(self):
        names = {
            0: '1 дэх өдөр (Даваа)',
            1: '2 дахь өдөр (Мягмар)',
            2: '3 дахь өдөр (Лхагва)',
            3: '4 дэх өдөр (Пүрэв)',
            4: '5 дахь өдөр (Баасан)',
            5: '6 дахь өдөр (Бямба)',
            6: '7 дахь өдөр (Ням)',
        }
        return ', '.join(names.get(day, str(day)) for day in self.get_weekday_numbers())


class CourseTeacherAssignment(models.Model):
    """Нэг ангид хэд хэдэн багш томилох холбоос"""
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='teacher_assignments',
        verbose_name='Сургалт'
    )
    teacher = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='course_assignments',
        limit_choices_to={'role__in': [
            UserRole.TEACHER_BEGINNER,
            UserRole.TEACHER_INTERMEDIATE,
            UserRole.TEACHER_ADVANCED,
        ]},
        verbose_name='Багш'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ангийн багшийн холбоос'
        verbose_name_plural = 'Ангийн багшийн холбоосууд'
        unique_together = ['course', 'teacher']
        ordering = ['course__name', 'teacher__last_name', 'teacher__first_name']

    def __str__(self):
        return f"{self.course.name} - {self.teacher.full_name}"


class AttendanceTeacherSelection(models.Model):
    """Ирцийн хүснэгтэд харагдах багш нарын сонголт"""
    course = models.OneToOneField(
        Course,
        on_delete=models.CASCADE,
        related_name='attendance_teacher_selection',
        verbose_name='Сургалт'
    )
    teacher_ids = models.TextField(verbose_name='Багшийн ID жагсаалт', blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ирцийн багшийн сонголт'
        verbose_name_plural = 'Ирцийн багшийн сонголтууд'

    def __str__(self):
        return f"{self.course.name} - {len(self.get_teacher_ids())} багш"

    def get_teacher_ids(self):
        teacher_ids = []
        for item in (self.teacher_ids or '').split(','):
            value = item.strip()
            if value.isdigit():
                teacher_ids.append(int(value))
        return sorted(set(teacher_ids))

    def set_teacher_ids(self, teacher_ids):
        cleaned = sorted({int(teacher_id) for teacher_id in teacher_ids if str(teacher_id).isdigit()})
        self.teacher_ids = ','.join(str(teacher_id) for teacher_id in cleaned)


class TeacherAttendance(models.Model):
    """Багш тухайн өдөр хичээл заасан эсэхийн бүртгэл"""
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='teacher_attendances',
        verbose_name='Сургалт'
    )
    teacher = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='teacher_attendances',
        limit_choices_to={'role__in': [
            UserRole.TEACHER_BEGINNER,
            UserRole.TEACHER_INTERMEDIATE,
            UserRole.TEACHER_ADVANCED,
        ]},
        verbose_name='Багш'
    )
    date = models.DateField(verbose_name='Огноо')
    present = models.BooleanField(default=True, verbose_name='Заасан')
    notes = models.TextField(verbose_name='Тэмдэглэл', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Багшийн ирц'
        verbose_name_plural = 'Багшийн ирцүүд'
        ordering = ['-date', 'teacher__last_name', 'teacher__first_name']
        unique_together = ['course', 'teacher', 'date']

    def __str__(self):
        status = 'Заасан' if self.present else 'Заагаагүй'
        return f"{self.teacher.full_name} - {self.course.name} - {self.date} ({status})"


class PageContent(models.Model):
    """Хуудасны агуулга - Админ эрхтэй хэрэглэгч засах боломжтой"""
    key = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Түлхүүр',
        help_text='Агуулгыг ялгах түлхүүр (жишээ: home_hero_title)'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='Гарчиг',
        help_text='Админ панел дээр харагдах нэр'
    )
    content = RichTextField(
        verbose_name='Агуулга',
        help_text='Вэб дээр харагдах текст (HTML форматчлалтай)',
        config_name='default'
    )
    page = models.CharField(
        max_length=50,
        verbose_name='Хуудас',
        choices=[
            ('home', 'Нүүр хуудас'),
            ('about', 'Бидний тухай'),
            ('courses', 'Хичээлүүд'),
            ('contact', 'Холбоо барих'),
            ('other', 'Бусад'),
        ],
        default='home'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Идэвхтэй',
        help_text='Вэб дээр харуулах эсэх'
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Шинэчилсэн')
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Шинэчилсэн хэрэглэгч'
    )
    
    class Meta:
        verbose_name = 'Хуудасны агуулга'
        verbose_name_plural = 'Хуудасны агуулгууд'
        ordering = ['page', 'key']
        permissions = [
            ('can_edit_content', 'Хуудасны агуулга засах эрхтэй'),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.key})"


# ========================================
# ДАНСНЫ ТӨЛӨВЛӨГӨӨ - Нягтлан бодох бүртгэл
# ========================================

class ChartOfAccounts(models.Model):
    """Дансны төлөвлөгөө - Нягтлан бодох бүртгэлийн дансууд"""
    
    ACCOUNT_TYPE_CHOICES = [
        ('ASSET', 'Актив'),
        ('LIABILITY', 'Пассив'),
        ('EQUITY', 'Өмч'),
        ('INCOME', 'Орлого'),
        ('EXPENSE', 'Зардал'),
        ('COST', 'Өртөг'),
    ]
    
    code = models.CharField('Дансны код', max_length=20, unique=True)
    name = models.CharField('Дансны нэр', max_length=255)
    account_type = models.CharField('Төрөл', max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                               verbose_name='Дээд данс', related_name='children')
    is_active = models.BooleanField('Идэвхтэй эсэх', default=True)
    description = models.TextField('Тайлбар', blank=True)
    
    # Үлдэгдэл
    opening_balance = models.DecimalField('Эхний үлдэгдэл', max_digits=15, decimal_places=2, default=0, 
                                         help_text='Систем ашиглаж эхлэхээс өмнөх үлдэгдэл')
    debit_balance = models.DecimalField('Дебит үлдэгдэл', max_digits=15, decimal_places=2, default=0)
    credit_balance = models.DecimalField('Кредит үлдэгдэл', max_digits=15, decimal_places=2, default=0)
    
    created_at = models.DateTimeField('Үүссэн огноо', auto_now_add=True)
    updated_at = models.DateTimeField('Шинэчилсэн огноо', auto_now=True)
    
    class Meta:
        ordering = ['code']
        verbose_name = 'Дансны төлөвлөгөө'
        verbose_name_plural = 'Дансны төлөвлөгөө'
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def balance(self):
        """Үлдэгдэл - Эхний үлдэгдэл + гүйлгээний дүн"""
        if self.account_type in ['ASSET', 'EXPENSE', 'COST']:
            # Актив/Зардал: Эхний үлдэгдэл + Дебит - Кредит
            return self.opening_balance + self.debit_balance - self.credit_balance
        else:  # LIABILITY, EQUITY, INCOME
            # Пассив/Өмч/Орлого: Эхний үлдэгдэл + Кредит - Дебит
            return self.opening_balance + self.credit_balance - self.debit_balance
    
    @property
    def level(self):
        """Дансны түвшин (кодны уртаар тодорхойлогдоно)"""
        return len(self.code)
    
    @property
    def is_parent(self):
        """Дээд данс эсэх"""
        return self.children.exists()


class AccountingEntry(models.Model):
    """Нягтлан бодох бүртгэлийн гүйлгээ (Журнал)"""
    
    entry_date = models.DateField('Гүйлгээний огноо')
    entry_number = models.CharField('Гүйлгээний дугаар', max_length=50, unique=True)
    description = models.TextField('Гүйлгээний утга')
    
    # Дебит
    debit_account = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT, 
                                      related_name='debit_entries', verbose_name='Дебит данс')
    debit_amount = models.DecimalField('Дебит дүн', max_digits=15, decimal_places=2)
    
    # Кредит
    credit_account = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT, 
                                       related_name='credit_entries', verbose_name='Кредит данс')
    credit_amount = models.DecimalField('Кредит дүн', max_digits=15, decimal_places=2)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                   verbose_name='Үүсгэсэн хэрэглэгч')
    created_at = models.DateTimeField('Үүссэн огноо', auto_now_add=True)
    related_sale = models.ForeignKey(
        'Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accounting_entries',
        verbose_name='Борлуулалт',
    )
    related_purchase = models.ForeignKey(
        'Purchase',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accounting_entries',
        verbose_name='Худалдан авалт',
    )

    class Meta:
        ordering = ['-entry_date', '-entry_number']
        verbose_name = 'Гүйлгээний бичилт'
        verbose_name_plural = 'Гүйлгээний бичилтүүд'
    
    def __str__(self):
        return f"{self.entry_number} - {self.entry_date}"
    
    def save(self, *args, **kwargs):
        """Хадгалах үед дансуудын үлдэгдэл шинэчлэх.

        Систем эхлэх огнооноос өмнөх (архивын) бичилт дансны үлдэгдэлд нөлөөлөхгүй —
        тэр хугацааны үлдэгдлийг эхний үлдэгдэл орлодог.
        """
        from .books_period import counts_in_balances
        is_new = self.pk is None
        
        if not is_new:
            # Хуучин утгыг буцаах
            old_entry = AccountingEntry.objects.get(pk=self.pk)
            if counts_in_balances(old_entry.entry_date):
                old_entry.debit_account.debit_balance -= old_entry.debit_amount
                old_entry.debit_account.save()
                old_entry.credit_account.credit_balance -= old_entry.credit_amount
                old_entry.credit_account.save()
        
        super().save(*args, **kwargs)
        
        # Шинэ үлдэгдэл тооцох
        if counts_in_balances(self.entry_date):
            self.debit_account.refresh_from_db(fields=['debit_balance'])
            self.debit_account.debit_balance += self.debit_amount
            self.debit_account.save()
            
            self.credit_account.refresh_from_db(fields=['credit_balance'])
            self.credit_account.credit_balance += self.credit_amount
            self.credit_account.save()
    
    def delete(self, *args, **kwargs):
        """Устгах үед дансуудын үлдэгдлээс дүн хасах"""
        from .books_period import counts_in_balances
        if counts_in_balances(self.entry_date):
            # Дебит дансны үлдэгдлээс хасах
            self.debit_account.refresh_from_db(fields=['debit_balance'])
            self.debit_account.debit_balance -= self.debit_amount
            self.debit_account.save()
            
            # Кредит дансны үлдэгдлээс хасах
            self.credit_account.refresh_from_db(fields=['credit_balance'])
            self.credit_account.credit_balance -= self.credit_amount
            self.credit_account.save()
        
        # Холбогдсон банкны гүйлгээний ангилал болон хуваарилалтыг цэвэрлэх
        bank_transactions = BankTransaction.objects.filter(accounting_entry=self)
        for bank_tx in bank_transactions:
            # Сурагчийн төлбөрийн хуваарилалт устгах
            bank_tx.allocations.all().delete()
            # Борлуулалтын хуваарилалт устгах
            bank_tx.sale_allocations.all().delete()
            # Гүйлгээний ангилал бүхэлд нь цэвэрлэх
            bank_tx.accounting_entry = None
            bank_tx.offset_account = None
            bank_tx.income_type = None
            bank_tx.income_student = None
            bank_tx.income_month = None
            bank_tx.income_year = None
            bank_tx.income_course = None
            bank_tx.income_sale = None
            bank_tx.is_processed = False
            bank_tx.save()
        
        super().delete(*args, **kwargs)


# ========================================
# БАРАА МАТЕРИАЛЫН УДИРДЛАГА
# ========================================

class ProductCategory(models.Model):
    """Бүтээгдэхүүний ангилал"""
    name = models.CharField(max_length=100, verbose_name='Ангиллын нэр', unique=True)
    description = models.TextField(verbose_name='Тайлбар', blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories',
        verbose_name='Эцэг ангилал'
    )
    is_active = models.BooleanField(default=True, verbose_name='Идэвхтэй эсэх')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Үүсгэсэн огноо')
    
    class Meta:
        verbose_name = 'Бүтээгдэхүүний ангилал'
        verbose_name_plural = 'Бүтээгдэхүүний ангиллууд'
        ordering = ['name']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name


class Product(models.Model):
    """Бүтээгдэхүүн/Бараа материал"""
    UNIT_CHOICES = [
        ('PIECE', 'Ширхэг'),
        ('BOX', 'Хайрцаг'),
        ('PACK', 'Багц'),
        ('KG', 'Кг'),
        ('LITER', 'Литр'),
        ('METER', 'Метр'),
        ('SET', 'Иж бүрдэл'),
    ]
    
    # Үндсэн мэдээлэл
    code = models.CharField(max_length=50, unique=True, verbose_name='Барааны код/SKU')
    name = models.CharField(max_length=200, verbose_name='Бүтээгдэхүүний нэр')
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Ангилал'
    )
    description = models.TextField(verbose_name='Тайлбар', blank=True)
    
    # Үнийн мэдээлэл
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Худалдан авах үнэ',
        help_text='Нийлүүлэгчээс авах үнэ'
    )
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Борлуулах үнэ',
        help_text='Үйлчлүүлэгчид зарах үнэ'
    )
    
    # Нэгж
    unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        default='PIECE',
        verbose_name='Хэмжих нэгж'
    )
    
    # Агуулах - Эхний үлдэгдэл нэмэгдсэн
    initial_stock = models.IntegerField(default=0, verbose_name='Эхний үлдэгдэл', help_text='Гараас оруулах эхний үлдэгдэл')
    min_stock = models.IntegerField(default=0, verbose_name='Доод үлдэгдэл', help_text='Сануулга өгөх үлдэгдэл')
    
    # Зураг
    image = models.ImageField(
        upload_to='products/',
        null=True,
        blank=True,
        verbose_name='Зураг'
    )
    
    # Нийлүүлэгч
    supplier = models.CharField(max_length=200, blank=True, verbose_name='Нийлүүлэгч (хуучин)')
    supplier_fk = models.ForeignKey(
        'Counterparty',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supplied_products',
        verbose_name='Нийлүүлэгч',
        limit_choices_to={'counterparty_type__in': ['SUPPLIER', 'BOTH']}
    )
    supplier_contact = models.CharField(max_length=100, blank=True, verbose_name='Холбоо барих (хуучин)')
    
    # Бусад
    is_active = models.BooleanField(default=True, verbose_name='Идэвхтэй эсэх')
    notes = models.TextField(blank=True, verbose_name='Тэмдэглэл')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Үүсгэсэн огноо')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Шинэчилсэн огноо')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_products',
        verbose_name='Үүсгэсэн хэрэглэгч'
    )
    
    class Meta:
        verbose_name = 'Бүтээгдэхүүн'
        verbose_name_plural = 'Бүтээгдэхүүнүүд'
        ordering = ['-created_at']
        permissions = [
            ('can_view_inventory', 'Бараа материал харах эрхтэй'),
            ('can_manage_inventory', 'Бараа материал удирдах эрхтэй'),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def current_stock(self):
        """
        Одоогийн үлдэгдэл = Эхний үлдэгдэл + Орлого - Зарлага
        StockMovement-ээс автоматаар тооцогдоно
        """
        from django.db.models import Sum, Q
        from .books_period import current_period_movements

        # Систем эхлэх огнооноос хойших хөдөлгөөн л тооцогдоно (өмнөхийг эхний үлдэгдэл орлоно)
        movements = current_period_movements(self.movements.all())
        
        # Орлого (IN, RETURN)
        income = movements.filter(
            movement_type__in=['IN', 'RETURN']
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        # Зарлага (OUT)
        expense = movements.filter(
            movement_type='OUT'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        # Тохируулга (ADJUSTMENT) - + эсвэл - байж болно
        adjustment = movements.filter(
            movement_type='ADJUSTMENT'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        return self.initial_stock + income - expense + adjustment
    
    @property
    def is_low_stock(self):
        """Үлдэгдэл бага эсэхийг шалгах"""
        return self.current_stock <= self.min_stock
    
    @property
    def profit_margin(self):
        """Ашгийн хувь тооцоолох"""
        if self.purchase_price and self.selling_price and self.purchase_price > 0:
            return ((self.selling_price - self.purchase_price) / self.purchase_price) * 100
        return 0
    
    @property
    def stock_value(self):
        """Үлдэгдлийн үнийн дүн"""
        if self.purchase_price:
            return self.current_stock * self.purchase_price
        return 0


class StockMovement(models.Model):
    """Агуулахын хөдөлгөөн (орлого/зарлага)"""
    MOVEMENT_TYPE_CHOICES = [
        ('IN', 'Орлого'),
        ('OUT', 'Зарлага'),
        ('ADJUSTMENT', 'Тохируулга'),
        ('RETURN', 'Буцаалт'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Бэлэн'),
        ('BANK', 'Данс'),
        ('MIXED', 'Бэлэн + Данс'),
        ('CREDIT', 'Зээлээр'),
        ('INTERNAL', 'Дотоод хэрэгцээ'),
        ('POS', 'POS карт'),
        ('CONVERSION', 'Бараа хувиргалт'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='movements',
        verbose_name='Бүтээгдэхүүн'
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPE_CHOICES,
        verbose_name='Төрөл'
    )
    quantity = models.IntegerField(verbose_name='Тоо ширхэг')
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Нэгж үнэ',
        help_text='Орлого бол худалдан авах үнэ, зарлага бол борлуулах үнэ'
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Нийт дүн',
        editable=False
    )
    
    # Санхүүгийн холбоос
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        verbose_name='Төлбөрийн хэлбэр',
        help_text='Бэлэн, данс эсвэл зээлээр'
    )
    bank_account = models.ForeignKey(
        'ChartOfAccounts',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements_account',
        verbose_name='Касс/Данс',
        help_text='1001-Касс эсвэл 1101-Банк'
    )
    counterparty = models.ForeignKey(
        'Counterparty',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Харилцагч',
        help_text='Нийлүүлэгч эсвэл үйлчлүүлэгч'
    )
    accounting_entry = models.ForeignKey(
        'AccountingEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Журналын бичилт'
    )
    
    # Холбогдох мэдээлэл
    reference_number = models.CharField(max_length=100, blank=True, verbose_name='Баримтын дугаар')
    customer_name = models.CharField(max_length=200, blank=True, verbose_name='Үйлчлүүлэгч/Нийлүүлэгч')
    
    # Борлуулагч (зөвхөн борлуулалтад)
    salesperson = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_made',
        verbose_name='Борлуулагч',
        help_text='Борлуулалт хийсэн менежер/ажилтан'
    )

    # Борлуулалтын баримтын холбоос (SET_NULL — Sale устгасан ч движение хэвээр үлдэнэ)
    sale = models.ForeignKey(
        'Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Борлуулалтын баримт'
    )

    # Худалдан авалт / бараа хувиргалтын баримт (засах, устгахад бүхэлд нь буцаахын тулд)
    purchase = models.ForeignKey(
        'Purchase',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Худалдан авалтын баримт'
    )

    notes = models.TextField(blank=True, verbose_name='Тэмдэглэл')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Огноо')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Бүртгэсэн хэрэглэгч'
    )
    
    class Meta:
        verbose_name = 'Агуулахын хөдөлгөөн'
        verbose_name_plural = 'Агуулахын хөдөлгөөнүүд'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product.name} ({self.quantity})"
    
    def save(self, *args, **kwargs):
        # Баримтын дугаар автоматаар үүсгэх
        if not self.reference_number:
            from datetime import datetime
            date_str = self.created_at.strftime('%Y%m%d') if self.created_at else datetime.now().strftime('%Y%m%d')
            
            # Төрлөөс хамаарч prefix сонгох
            if self.movement_type == 'IN':
                prefix = 'INV-IN'
            elif self.movement_type == 'OUT':
                prefix = 'INV-OUT'
            elif self.movement_type == 'ADJUSTMENT':
                prefix = 'INV-ADJ'
            elif self.movement_type == 'RETURN':
                prefix = 'INV-RET'
            else:
                prefix = 'INV'
            
            # Өнөөдрийн сүүлийн дугаар олох
            last_movement = StockMovement.objects.filter(
                reference_number__startswith=f'{prefix}-{date_str}'
            ).order_by('-reference_number').first()
            
            if last_movement:
                # Сүүлийн дугаарыг задлах (INV-IN-20260209-001 → 001)
                try:
                    last_num = int(last_movement.reference_number.split('-')[-1])
                    next_num = last_num + 1
                except (ValueError, IndexError):
                    next_num = 1
            else:
                next_num = 1
            
            self.reference_number = f'{prefix}-{date_str}-{next_num:03d}'
        
        # Нийт дүн тооцоолох
        self.total_amount = self.quantity * self.price
        
        # current_stock нь @property тул тусад нь шинэчлэх шаардлагагүй —
        # StockMovement хадгалагдсаны дараа автоматаар тооцоологдоно.
        
        super().save(*args, **kwargs)


# ========================================
# SIGNALS
# ========================================

@receiver(pre_save, sender=UserProfile)
def remember_previous_role(sender, instance, **kwargs):
    """Хадгалахын өмнөх эрхийг санах (эрх солигдсоныг илрүүлэхэд)"""
    instance._previous_role = None
    if instance.pk:
        instance._previous_role = (
            sender.objects.filter(pk=instance.pk).values_list('role', flat=True).first()
        )


@receiver(post_save, sender=UserProfile)
def update_user_staff_status(sender, instance, created, **kwargs):
    """
    Менежер, нягтлан, админ эрхтэй хэрэглэгчдэд автоматаар staff статус өгөх.
    Эрх солигдоход (сурагч → менежер, менежер → сурагч г.м.) дагалдах
    өөрчлөлтийг хийнэ. Түүхэн бичлэг (ирц, төлбөр) устгагдахгүй.
    """
    user = instance.user
    old_role = getattr(instance, '_previous_role', None)
    new_role = instance.role

    if new_role in STAFF_ROLES:
        if not user.is_staff:
            user.is_staff = True
            user.save(update_fields=['is_staff'])

    if created or not old_role or old_role == new_role:
        return

    # Staff эрхтэй байснаас энгийн эрх рүү шилжвэл staff эрхийг хасах
    if old_role in STAFF_ROLES and new_role not in STAFF_ROLES and not user.is_superuser:
        if user.is_staff:
            user.is_staff = False
            user.save(update_fields=['is_staff'])

    # Сурагч биш болсон: идэвхтэй бүртгэлүүдийг идэвхгүй болгох (устгахгүй)
    if old_role == UserRole.STUDENT:
        Enrollment.objects.filter(student=instance, is_active=True).update(is_active=False)
        UserProfile.objects.filter(pk=instance.pk).update(is_active_student=False)
        instance.is_active_student = False

    # Сурагч болсон: идэвхтэй сурагч гэж тэмдэглэх
    if new_role == UserRole.STUDENT:
        UserProfile.objects.filter(pk=instance.pk).update(is_active_student=True)
        instance.is_active_student = True

    # Багш биш болсон: идэвхтэй ангиудаас чөлөөлөх (дууссан ангийн түүх хэвээр)
    if old_role in TEACHER_ROLES and new_role not in TEACHER_ROLES:
        CourseTeacherAssignment.objects.filter(teacher=instance, course__is_active=True).delete()
        Course.objects.filter(teacher=instance, is_active=True).update(teacher=None)


# ========================================
# САНХҮҮГИЙН МОДУЛИУД
# ========================================

class Account(models.Model):
    """Данс - Касс, Банкны данс"""
    ACCOUNT_TYPE_CHOICES = [
        ('CASH', 'Касс'),
        ('BANK', 'Банкны данс'),
        ('CARD', 'Картын данс'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Дансны нэр')
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        verbose_name='Төрөл'
    )
    account_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Дансны дугаар'
    )
    bank_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Банкны нэр'
    )
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Үлдэгдэл'
    )
    is_active = models.BooleanField(default=True, verbose_name='Идэвхтэй эсэх')
    notes = models.TextField(blank=True, verbose_name='Тэмдэглэл')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Үүсгэсэн огноо')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Шинэчилсэн огноо')
    
    class Meta:
        verbose_name = 'Данс'
        verbose_name_plural = 'Дансууд'
        ordering = ['account_type', 'name']
    
    def __str__(self):
        return f"{self.get_account_type_display()} - {self.name}"


class Counterparty(models.Model):
    """Харилцагч - Нийлүүлэгч, үйлчлүүлэгч"""
    COUNTERPARTY_TYPE_CHOICES = [
        ('SUPPLIER', 'Нийлүүлэгч'),
        ('CUSTOMER', 'Үйлчлүүлэгч'),
        ('BOTH', 'Хоёулаа'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Нэр', unique=True)
    counterparty_type = models.CharField(
        max_length=20,
        choices=COUNTERPARTY_TYPE_CHOICES,
        default='BOTH',
        verbose_name='Төрөл'
    )
    contact_person = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Холбоо барих хүн'
    )
    phone = models.CharField(max_length=50, blank=True, verbose_name='Утас')
    email = models.EmailField(blank=True, verbose_name='Имэйл')
    address = models.TextField(blank=True, verbose_name='Хаяг')
    
    # Регистр, татвар
    registration_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Регистрийн дугаар'
    )
    tax_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Татварын дугаар'
    )
    
    # Тооцоо
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Харилцах үлдэгдэл',
        help_text='Эерэг = Манай өр, Сөрөг = Тэдний өр'
    )
    
    # Дансны мэдээлэл
    default_income_account = models.ForeignKey(
        'ChartOfAccounts',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='counterparty_income',
        verbose_name='Орлогын данс',
        help_text='Энэ харилцагчаас орлого орохдоо ашиглах данс (4xxx)',
        limit_choices_to={'account_type': 'INCOME', 'is_active': True}
    )
    default_expense_account = models.ForeignKey(
        'ChartOfAccounts',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='counterparty_expense',
        verbose_name='Зардлын данс',
        help_text='Энэ харилцагч руу зарлага гарахдаа ашиглах данс (5xxx)',
        limit_choices_to={'account_type': 'EXPENSE', 'is_active': True}
    )
    
    # Сурагч/ажилтантай холбох (нэг хүн хоёр газар давхар бүртгэгдэхээс сэргийлнэ)
    profile = models.OneToOneField(
        'UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='counterparty',
        verbose_name='Холбогдсон хэрэглэгч'
    )

    is_active = models.BooleanField(default=True, verbose_name='Идэвхтэй эсэх')
    notes = models.TextField(blank=True, verbose_name='Тэмдэглэл')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Үүсгэсэн огноо')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Шинэчилсэн огноо')
    
    class Meta:
        verbose_name = 'Харилцагч'
        verbose_name_plural = 'Харилцагчид'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_counterparty_type_display()})"


class CashFlowIndicator(models.Model):
    """Мөнгөн гүйлгээний үзүүлэлт"""
    
    FLOW_TYPE_CHOICES = [
        ('INCOME', 'Орлого'),
        ('EXPENSE', 'Зарлага'),
        ('BOTH', 'Хоёулаа'),
    ]
    
    code = models.CharField('Код', max_length=10, unique=True, 
                           help_text='Жишээ: 1.1.1')
    name = models.CharField('Нэр', max_length=255,
                           help_text='Үзүүлэлтийн нэр')
    flow_type = models.CharField('Төрөл', max_length=10, choices=FLOW_TYPE_CHOICES,
                                 help_text='Орлого эсвэл зарлага')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, 
                              null=True, blank=True,
                              related_name='children',
                              verbose_name='Эцэг үзүүлэлт')
    level = models.PositiveSmallIntegerField('Түвшин', default=1,
                                            help_text='Үзүүлэлтийн түвшин (1, 2, 3...)')
    is_active = models.BooleanField('Идэвхтэй', default=True)
    sort_order = models.PositiveSmallIntegerField('Эрэмбэ', default=0)
    
    created_at = models.DateTimeField('Үүсгэсэн огноо', auto_now_add=True)
    updated_at = models.DateTimeField('Шинэчилсэн огноо', auto_now=True)
    
    class Meta:
        verbose_name = 'Мөнгөн гүйлгээний үзүүлэлт'
        verbose_name_plural = 'Мөнгөн гүйлгээний үзүүлэлтүүд'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class BankTransaction(models.Model):
    """Банк болон кассын гүйлгээ - Анхны өгөгдөл"""
    
    ACCOUNT_TYPE_CHOICES = [
        ('BANK', 'Банк'),
        ('CASH', 'Касс'),
    ]
    
    BANK_CHOICES = [
        ('KHAN', 'Хаан банк'),
        ('GOLOMT', 'Голомт банк'),
        ('TDB', 'Худалдаа хөгжлийн банк'),
        ('STATE', 'Төрийн банк'),
        ('XAC', 'Хас банк'),
        ('CASH_REGISTER', 'Касс'),
        ('OTHER', 'Бусад'),
    ]
    
    INCOME_TYPE_CHOICES = [
        ('STUDENT_PAYMENT', 'Сурагчийн төлбөр'),
        ('PRODUCT_SALE', 'Барааны борлуулалт'),
        ('SERVICE_FEE', 'Үйлчилгээний төлбөр'),
        ('DONATION', 'Хандив'),
        ('OTHER', 'Бусад орлого'),
    ]



    
    EXPENSE_TYPE_CHOICES = [
        ('PRODUCT_PURCHASE', 'Бараа материалын худалдан авалт'),
        ('SALARY', 'Цалин'),
        ('RENT', 'Түрээс'),
        ('UTILITIES', 'Ахуйн зардал (цахилгаан, ус гэх мэт)'),
        ('MARKETING', 'Сурталчилгаа'),
        ('OFFICE_SUPPLIES', 'Оффисын хэрэгсэл'),
        ('TRANSPORTATION', 'Тээвэр'),
        ('OTHER', 'Бусад зардал'),
    ]
    
    # Дансны төрөл
    account_type = models.CharField(
        'Дансны төрөл',
        max_length=10,
        choices=ACCOUNT_TYPE_CHOICES,
        default='BANK',
        help_text='Банкны данс эсвэл касс'
    )
    
    # Банк/Кассын мэдээлэл
    bank_name = models.CharField('Банк/Кассын нэр', max_length=50, choices=BANK_CHOICES)
    bank_account = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT, 
                                     verbose_name='Данс',
                                     help_text='Дансны төлөвлөгөөний банк (110x) эсвэл касс (100x, 101x) данс')
    
    # Гүйлгээний мэдээлэл
    transaction_date = models.DateField('Гүйлгээний огноо')
    transaction_time = models.TimeField('Гүйлгээний цаг', null=True, blank=True)
    description = models.TextField('Гүйлгээний утга')
    
    # Харилцагч
    counterparty_account = models.CharField('Харьцсан данс', max_length=100, blank=True)
    counterparty_name = models.CharField('Харьцсан дансны нэр', max_length=255, blank=True)
    counterparty = models.ForeignKey(Counterparty, on_delete=models.SET_NULL, 
                                    null=True, blank=True, verbose_name='Харилцагч')
    transfer_source = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='transfer_mirrors',
        verbose_name='Эх гүйлгээ',
        help_text='Автоматаар үүссэн кассын эсрэг мөр бол үүсгэсэн банк/кассын гүйлгээ',
    )
    
    # Дүн (Хаан банк: Дебит/Кредит, Голомт банк: Орлого/Зарлага)
    income_amount = models.DecimalField('Орлого', max_digits=15, decimal_places=2, default=0,
                                       help_text='Данс руу орсон дүн')
    expense_amount = models.DecimalField('Зарлага', max_digits=15, decimal_places=2, default=0,
                                        help_text='Дансаас гарсан дүн')
    
    # Орлогын ангилал (орлого бол)
    income_type = models.CharField('Орлогын төрөл', max_length=50, 
                                   choices=INCOME_TYPE_CHOICES, null=True, blank=True,
                                   help_text='Орлогын гүйлгээний төрөл')
    
    # Зарлагын ангилал (зарлага бол)
    expense_type = models.CharField('Зарлагын төрөл', max_length=50,
                                    choices=EXPENSE_TYPE_CHOICES, null=True, blank=True,
                                    help_text='Зарлагын гүйлгээний төрөл')
    
    income_student = models.ForeignKey('UserProfile', on_delete=models.SET_NULL, 
                                      null=True, blank=True,
                                      verbose_name='Сурагч',
                                      help_text='Сурагчийн төлбөр бол ямар сурагч')
    income_course = models.ForeignKey('Course', on_delete=models.SET_NULL,
                                     null=True, blank=True,
                                     verbose_name='Анги',
                                     help_text='Сурагчийн төлбөр бол ямар анги')
    income_month = models.PositiveSmallIntegerField('Төлбөрийн сар', null=True, blank=True,
                                                    help_text='Хэддүгээр сарын төлбөр (1-12)')
    income_year = models.PositiveSmallIntegerField('Төлбөрийн он', null=True, blank=True,
                                                   help_text='Хэддүгээр оны төлбөр (жишээ: 2026)')
    income_sale = models.ForeignKey('Sale', on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   verbose_name='Борлуулалт',
                                   help_text='Барааны борлуулалт бол холбогдох борлуулалтын бүртгэл')
    
    # Төлбөрийн тэмдэглэл
    payment_comment = models.TextField('Тэмдэглэл', blank=True, 
                                       help_text='Төлбөрийн тухай тэмдэглэл, анхааруулга')
    payment_color = models.CharField('Өнгө', max_length=7, blank=True, default='',
                                     help_text='Төлбөрийн нүдний өнгө (жишээ: #ff0000)')
    
    # Мөнгөн гүйлгээний үзүүлэлт
    cash_flow_indicator = models.ForeignKey('CashFlowIndicator', on_delete=models.SET_NULL,
                                           null=True, blank=True,
                                           verbose_name='Мөнгөн гүйлгээний үзүүлэлт',
                                           help_text='Мөнгөн гүйлгээний тайланд ямар үзүүлэлтэнд хамаарах')
    
    # Үлдэгдэл
    opening_balance = models.DecimalField('Эхний үлдэгдэл', max_digits=15, decimal_places=2, 
                                         null=True, blank=True)
    closing_balance = models.DecimalField('Эцсийн үлдэгдэл', max_digits=15, decimal_places=2, 
                                         null=True, blank=True)
    
    # Бусад
    branch_code = models.CharField('Салбарын код', max_length=20, blank=True)
    reference_number = models.CharField('Гүйлгээний дугаар', max_length=50, blank=True, db_index=True,
                                        help_text='Банкны хуулгын гүйлгээний дугаар (давхардал шалгахад)')
    exchange_rate = models.DecimalField('Ханш', max_digits=10, decimal_places=4, 
                                       null=True, blank=True)
    
    # Эсрэг данс (ажилтан гараар холбоно)
    offset_account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bank_transactions_offset',
        verbose_name='Эсрэг данс',
        help_text='Орлого бол кредит данс (4xxx), зарлага бол дебит данс (5xxx)'
    )
    
    # Систем
    accounting_entry = models.ForeignKey(AccountingEntry, on_delete=models.SET_NULL, 
                                        null=True, blank=True, 
                                        verbose_name='Гүйлгээний бичилт',
                                        help_text='Үүссэн журналын бичилт')
    is_processed = models.BooleanField('Боловсруулсан эсэх', default=False)
    imported_at = models.DateTimeField('Импортолсон огноо', auto_now_add=True)
    imported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                   verbose_name='Импортолсон хэрэглэгч')
    
    class Meta:
        ordering = ['-transaction_date', '-transaction_time']
        verbose_name = 'Банкны гүйлгээ'
        verbose_name_plural = 'Банкны гүйлгээнүүд'
        indexes = [
            models.Index(fields=['bank_account', 'transaction_date']),
            models.Index(fields=['is_processed']),
        ]
    
    def __str__(self):
        amount = self.income_amount if self.income_amount > 0 else self.expense_amount
        direction = "+" if self.income_amount > 0 else "-"
        return f"{self.transaction_date} | {direction}{amount:,.0f}₮ | {self.description[:50]}"
    
    @property
    def amount(self):
        """Гүйлгээний дүн (орлого бол эерэг, зарлага бол сөрөг)"""
        return self.income_amount - self.expense_amount

    @property
    def student_allocated_amount(self):
        """Сурагчийн төлбөрт хуваарилсан нийт дүн"""
        return self.allocations.aggregate(total=Sum('amount'))['total'] or 0

    @property
    def sale_allocated_amount(self):
        """Борлуулалт руу хуваарилсан нийт дүн"""
        return self.sale_allocations.aggregate(total=Sum('amount'))['total'] or 0

    @property
    def available_income_amount(self):
        """Цааш хуваарилж болох үлдсэн орлогын дүн"""
        reserved = self.student_allocated_amount + self.sale_allocated_amount
        remaining = self.income_amount - reserved
        return remaining if remaining > 0 else 0

    @property
    def transfer_link(self):
        """Харилцах хоорондын шилжүүлгийн холбоос (орлого эсвэл зарлагын тал), байхгүй бол None"""
        for attr in ('transfer_link_as_expense', 'transfer_link_as_income'):
            try:
                return getattr(self, attr)
            except ObjectDoesNotExist:
                continue
        return None


class IncomeCategory(models.Model):
    """Орлогын төрөл - админд нэмэлтээр нэмэх боломжтой"""
    code = models.CharField('Код', max_length=50, unique=True)
    name = models.CharField('Нэр', max_length=200)

    class Meta:
        verbose_name = 'Орлогын төрөл'
        verbose_name_plural = 'Орлогын төрөлүүд'
        ordering = ['name']

    def __str__(self):
        return self.name


class PaymentAllocation(models.Model):
    """Төлбөрийн хуваарилалт - нэг банкны гүйлгээг олон сурагч/сар/анги-д хуваарилах"""
    transaction = models.ForeignKey(
        BankTransaction,
        on_delete=models.CASCADE,
        related_name='allocations',
        verbose_name='Банкны гүйлгээ'
    )
    student = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        verbose_name='Сурагч',
        limit_choices_to={'role': UserRole.STUDENT}
    )
    course = models.ForeignKey(
        'Course',
        on_delete=models.CASCADE,
        verbose_name='Анги'
    )
    month = models.PositiveSmallIntegerField(
        'Сар',
        help_text='Хэддүгээр сарын төлбөр (1-12)'
    )
    year = models.PositiveSmallIntegerField(
        'Он',
        help_text='Хэддүгээр оны төлбөр (жишээ: 2026)'
    )
    amount = models.DecimalField(
        'Дүн',
        max_digits=15,
        decimal_places=2,
        help_text='Энэ сурагч/сар/анги-д хуваарилсан дүн'
    )
    
    # Төлбөрийн тэмдэглэл (мөр бүрт өөрөө байж болно)
    comment = models.TextField('Тэмдэглэл', blank=True)
    color = models.CharField('Өнгө', max_length=7, blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Төлбөрийн хуваарилалт'
        verbose_name_plural = 'Төлбөрийн хуваарилалтууд'
        ordering = ['transaction', 'student', 'year', 'month']
    
    def __str__(self):
        return f"{self.student.mongolian_name} - {self.course.name} - {self.year}/{self.month} - {self.amount:,.0f}₮"


class PendingPayment(models.Model):
    """Хуулга импортлохоос өмнө "төлсөн" гэж тэмдэглэсэн сурагчийн төлбөр.

    Банк/кассын гүйлгээнд ижил сурагч/анги/сарын PaymentAllocation үүсэхэд
    автоматаар холбогдоно (allocation). Холболт цуцлагдвал дахин хүлээгдэнэ.
    Баталгаажсан төлбөрийн дүн, журнал зөвхөн PaymentAllocation-аас тооцогдоно.
    """
    METHOD_CHOICES = [
        ('BANK', 'Банкаар'),
        ('CASH', 'Бэлнээр'),
        ('POS', 'POS-оор'),
        ('OTHER', 'Бусад'),
    ]

    student = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='pending_payments',
        verbose_name='Сурагч',
        limit_choices_to={'role': UserRole.STUDENT}
    )
    course = models.ForeignKey('Course', on_delete=models.CASCADE, verbose_name='Анги')
    month = models.PositiveSmallIntegerField('Сар')
    year = models.PositiveSmallIntegerField('Он')
    amount = models.DecimalField('Дүн', max_digits=15, decimal_places=2)
    paid_date = models.DateField('Төлсөн огноо')
    method = models.CharField('Төлсөн хэлбэр', max_length=10, choices=METHOD_CHOICES, default='BANK')
    payer_name = models.CharField('Төлөгчийн нэр/данс', max_length=255, blank=True,
                                  help_text='Хуулгатай тааруулахад ашиглана')
    comment = models.TextField('Тэмдэглэл', blank=True)
    pre_start = models.BooleanField(
        'Систем эхлэхээс өмнө төлсөн', default=False,
        help_text='Кассын гүйлгээ, журналгүйгээр төлсөн гэж тооцно; хуулгатай холбогдохгүй'
    )
    allocation = models.OneToOneField(
        PaymentAllocation,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pending_payment',
        verbose_name='Холбогдсон хуваарилалт'
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name='Тэмдэглэсэн')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Хуулга хүлээж буй төлбөр'
        verbose_name_plural = 'Хуулга хүлээж буй төлбөрүүд'
        ordering = ['paid_date', 'id']

    def __str__(self):
        return f"{self.student} - {self.course.name} - {self.year}/{self.month} - {self.amount:,.0f}₮"

    @property
    def is_matched(self):
        return self.allocation_id is not None


class PaymentDiscount(models.Model):
    """Сурагчийн тухайн анги/сарын төлбөрийн хөнгөлөлт (ж: "Эхний сар үнэгүй").

    Сарын төлбөрөөс хасагдаж, төлөв, өрийг хөнгөлөлтийн дараах дүнгээр тооцно.
    """
    KIND_CHOICES = [
        ('PERCENT', 'Хувь (%)'),
        ('AMOUNT', 'Дүн (₮)'),
    ]

    student = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='payment_discounts',
        verbose_name='Сурагч',
        limit_choices_to={'role': UserRole.STUDENT}
    )
    course = models.ForeignKey('Course', on_delete=models.CASCADE, verbose_name='Анги')
    year = models.PositiveSmallIntegerField('Он')
    month = models.PositiveSmallIntegerField('Сар')
    name = models.CharField('Хөнгөлөлтийн нэр', max_length=100)
    kind = models.CharField('Төрөл', max_length=10, choices=KIND_CHOICES, default='PERCENT')
    value = models.DecimalField('Хэмжээ', max_digits=15, decimal_places=2)
    comment = models.TextField('Тайлбар', blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name='Бүртгэсэн')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Төлбөрийн хөнгөлөлт'
        verbose_name_plural = 'Төлбөрийн хөнгөлөлтүүд'
        unique_together = ['student', 'course', 'year', 'month']
        ordering = ['year', 'month']

    def __str__(self):
        return f"{self.student} - {self.course.name} - {self.year}/{self.month} - {self.name}"

    def amount_for(self, fee):
        """Сарын төлбөрөөс хасагдах дүн (төлбөрөөс хэтрэхгүй)."""
        fee = fee or Decimal('0')
        if self.kind == 'PERCENT':
            amount = fee * self.value / Decimal('100')
        else:
            amount = self.value
        return max(min(amount, fee), Decimal('0'))

    @property
    def label(self):
        return f'{self.value:.0f}%' if self.kind == 'PERCENT' else f'{self.value:,.0f}₮'


class PaymentCellNote(models.Model):
    """Сурагчдын төлбөрийн хүснэгтийн нүдний (сурагч/анги/сар) тэмдэглэл, өнгө."""
    student = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='payment_cell_notes',
        verbose_name='Сурагч',
        limit_choices_to={'role': UserRole.STUDENT}
    )
    course = models.ForeignKey('Course', on_delete=models.CASCADE, verbose_name='Анги')
    month = models.PositiveSmallIntegerField('Сар')
    year = models.PositiveSmallIntegerField('Он')
    comment = models.TextField('Тэмдэглэл', blank=True)
    color = models.CharField('Өнгө', max_length=7, blank=True, default='')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name='Засварласан')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Төлбөрийн нүдний тэмдэглэл'
        verbose_name_plural = 'Төлбөрийн нүдний тэмдэглэлүүд'
        constraints = [
            models.UniqueConstraint(fields=['student', 'course', 'year', 'month'], name='unique_payment_cell_note'),
        ]

    def __str__(self):
        return f"{self.student} - {self.course.name} - {self.year}/{self.month}"


@receiver(post_save, sender=PaymentAllocation)
def match_pending_payment(sender, instance, created, **kwargs):
    """Шинэ хуваарилалтыг ижил сурагч/анги/сарын хүлээгдэж буй тэмдэглэлтэй холбоно."""
    if not created:
        return
    pending = PendingPayment.objects.filter(
        student_id=instance.student_id, course_id=instance.course_id,
        year=instance.year, month=instance.month, allocation__isnull=True, pre_start=False,
    ).first()
    if pending:
        pending.allocation = instance
        pending.save(update_fields=['allocation'])


class BankTransferLink(models.Model):
    """Хоёр банкны дансны хоорондын шилжүүлгийн хос холбоос."""
    income_transaction = models.OneToOneField(
        BankTransaction,
        on_delete=models.CASCADE,
        related_name='transfer_link_as_income',
        verbose_name='Орлогын гүйлгээ'
    )
    expense_transaction = models.OneToOneField(
        BankTransaction,
        on_delete=models.CASCADE,
        related_name='transfer_link_as_expense',
        verbose_name='Зарлагын гүйлгээ'
    )
    amount = models.DecimalField('Дүн', max_digits=15, decimal_places=2)
    accounting_entry = models.OneToOneField(
        AccountingEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bank_transfer_link',
        verbose_name='Журналын бичилт'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Үүсгэсэн хэрэглэгч'
    )
    created_at = models.DateTimeField('Үүсгэсэн огноо', auto_now_add=True)

    class Meta:
        verbose_name = 'Харилцах хоорондын шилжүүлэг'
        verbose_name_plural = 'Харилцах хоорондын шилжүүлгүүд'

    def __str__(self):
        return f"#{self.income_transaction_id} → #{self.expense_transaction_id} ({self.amount:,.0f}₮)"


class SalePaymentAllocation(models.Model):
    """Нэг банкны гүйлгээг борлуулалтад дүнгээр нь хуваарилж холбох"""
    transaction = models.ForeignKey(
        BankTransaction,
        on_delete=models.CASCADE,
        related_name='sale_allocations',
        verbose_name='Банкны гүйлгээ'
    )
    sale = models.ForeignKey(
        'Sale',
        on_delete=models.CASCADE,
        related_name='payment_allocations',
        verbose_name='Борлуулалт'
    )
    amount = models.DecimalField(
        'Холбосон дүн',
        max_digits=15,
        decimal_places=2,
        help_text='Энэ гүйлгээнээс тухайн борлуулалтад холбосон дүн'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Борлуулалтын төлбөрийн хуваарилалт'
        verbose_name_plural = 'Борлуулалтын төлбөрийн хуваарилалтууд'
        unique_together = ['transaction', 'sale']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sale.sale_number} - #{self.transaction_id} - {self.amount:,.0f}₮"


class Transaction(models.Model):
    """Гүйлгээ - Мөнгөн хөрөнгийн орлого/зарлага"""
    TRANSACTION_TYPE_CHOICES = [
        ('INCOME', 'Орлого'),
        ('EXPENSE', 'Зарлага'),
        ('TRANSFER', 'Шилжүүлэг'),
    ]
    
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        verbose_name='Төрөл'
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Дүн'
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name='Данс'
    )
    to_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transfers_in',
        verbose_name='Хүлээн авах данс',
        help_text='Зөвхөн шилжүүлэг үед'
    )
    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='Харилцагч'
    )
    
    description = models.CharField(max_length=500, verbose_name='Утга')
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Баримтын дугаар'
    )
    transaction_date = models.DateField(verbose_name='Огноо')
    
    # Холбогдох бүртгэлүүд
    related_purchase = models.ForeignKey(
        'Purchase',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Худалдан авалт'
    )
    related_sale = models.ForeignKey(
        'Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Борлуулалт'
    )
    
    notes = models.TextField(blank=True, verbose_name='Тэмдэглэл')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Үүсгэсэн огноо')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Үүсгэсэн хэрэглэгч'
    )
    
    class Meta:
        verbose_name = 'Гүйлгээ'
        verbose_name_plural = 'Гүйлгээнүүд'
        ordering = ['-transaction_date', '-created_at']
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount}₮ ({self.transaction_date})"
    
    def save(self, *args, **kwargs):
        """Дансны үлдэгдэл шинэчлэх"""
        if self.pk is None:  # Шинээр үүсгэж байгаа бол
            if self.transaction_type == 'INCOME':
                self.account.balance += self.amount
                self.account.save()
            elif self.transaction_type == 'EXPENSE':
                self.account.balance -= self.amount
                self.account.save()
            elif self.transaction_type == 'TRANSFER' and self.to_account:
                self.account.balance -= self.amount
                self.to_account.balance += self.amount
                self.account.save()
                self.to_account.save()
        
        super().save(*args, **kwargs)


class Purchase(models.Model):
    """Худалдан авалт / бараа хувиргалтын баримт.

    Бараанууд нь StockMovement (purchase=self): худалдан авалтад IN, хувиргалтад
    гарц бараа IN + зарцуулсан бэлдэц OUT. Журнал нь AccountingEntry.related_purchase.
    """
    KIND_CHOICES = [
        ('PURCHASE', 'Худалдан авалт'),
        ('CONVERSION', 'Бараа хувиргалт'),
    ]
    STATUS_CHOICES = [
        ('DRAFT', 'Ноорог'),
        ('ORDERED', 'Захиалсан'),
        ('RECEIVED', 'Хүлээн авсан'),
        ('PAID', 'Төлсөн'),
        ('COMPLETED', 'Дууссан'),
        ('CANCELLED', 'Цуцалсан'),
    ]
    
    purchase_number = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        verbose_name='Худалдан авалтын дугаар'
    )
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='PURCHASE', verbose_name='Төрөл')
    supplier = models.ForeignKey(
        Counterparty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchases',
        verbose_name='Нийлүүлэгч'
    )
    purchase_date = models.DateField(verbose_name='Огноо')
    payment_method = models.CharField(max_length=20, blank=True, verbose_name='Төлбөрийн хэлбэр')
    reference_number = models.CharField(max_length=100, blank=True, verbose_name='Баримтын дугаар')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name='Төлөв'
    )
    
    # Бүтээгдэхүүнүүд
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Нийт дүн'
    )
    paid_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Төлсөн дүн'
    )
    
    # Төлбөр
    payment_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Төлбөрийн данс'
    )
    payment_date = models.DateField(null=True, blank=True, verbose_name='Төлсөн огноо')
    
    notes = models.TextField(blank=True, verbose_name='Тэмдэглэл')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Үүсгэсэн огноо')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Шинэчилсэн огноо')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Үүсгэсэн хэрэглэгч'
    )
    
    class Meta:
        verbose_name = 'Худалдан авалт'
        verbose_name_plural = 'Худалдан авалтууд'
        ordering = ['-purchase_date', '-created_at']
    
    def __str__(self):
        return f"{self.purchase_number} - {self.supplier.name if self.supplier else self.get_kind_display()}"
    
    @property
    def remaining_amount(self):
        """Үлдэгдэл төлбөр"""
        return self.total_amount - self.paid_amount
    
    @property
    def is_fully_paid(self):
        """Бүрэн төлсөн эсэх"""
        return self.paid_amount >= self.total_amount
    
    def save(self, *args, **kwargs):
        """Хадгалахдаа дугаар автоматаар үүсгэх"""
        if not self.purchase_number:
            # Огнооны формат: PUR-YYYYMMDD-XXX
            from datetime import datetime
            date_str = self.purchase_date.strftime('%Y%m%d')
            
            # Өнөөдрийн сүүлийн дугаар олох
            last_purchase = Purchase.objects.filter(
                purchase_number__startswith=f'PUR-{date_str}'
            ).order_by('-purchase_number').first()
            
            if last_purchase:
                # Сүүлийн дугаарыг задлах (PUR-20260209-001 → 001)
                last_num = int(last_purchase.purchase_number.split('-')[-1])
                next_num = last_num + 1
            else:
                next_num = 1
            
            self.purchase_number = f'PUR-{date_str}-{next_num:03d}'
        
        super().save(*args, **kwargs)


class PurchaseItem(models.Model):
    """Худалдан авалтын зүйл"""
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Худалдан авалт'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name='Бүтээгдэхүүн'
    )
    quantity = models.IntegerField(verbose_name='Тоо ширхэг')
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Нэгж үнэ'
    )
    total_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Нийт үнэ',
        editable=False
    )
    
    class Meta:
        verbose_name = 'Худалдан авалтын зүйл'
        verbose_name_plural = 'Худалдан авалтын зүйлүүд'
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class Sale(models.Model):
    """Борлуулалт"""
    STATUS_CHOICES = [
        ('DRAFT', 'Ноорог'),
        ('CONFIRMED', 'Баталсан'),
        ('DELIVERED', 'Хүргэсэн'),
        ('PAID', 'Төлсөн'),
        ('COMPLETED', 'Дууссан'),
        ('CANCELLED', 'Цуцалсан'),
    ]
    
    sale_number = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        verbose_name='Борлуулалтын дугаар'
    )
    customer = models.ForeignKey(
        Counterparty,
        on_delete=models.PROTECT,
        limit_choices_to={'counterparty_type__in': ['CUSTOMER', 'BOTH']},
        related_name='sales',
        verbose_name='Үйлчлүүлэгч',
        null=True,
        blank=True
    )
    sale_date = models.DateField(verbose_name='Огноо')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name='Төлөв'
    )
    
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Нийт дүн'
    )
    paid_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Төлсөн дүн'
    )
    
    # Төлбөр
    payment_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Төлбөрийн данс'
    )
    payment_date = models.DateField(null=True, blank=True, verbose_name='Төлсөн огноо')
    
    notes = models.TextField(blank=True, verbose_name='Тэмдэглэл')

    # Импортын мэдээлэл
    salesperson_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Хүлээн авсан хүн',
        help_text='Борлуулалт буюу төлбөр хүлээн авсан ажилтны нэр'
    )
    pos_bank_account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pos_sales',
        verbose_name='POS-ын банк',
        help_text='POS картаар төлсөн бол аль банкны POS (сэттлмэнттэй тулгахад ашиглана)',
    )
    expected_payment_method = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Төлбөрийн хэлбэр (таамаглал)',
        help_text='Касс / Харилцах / Хоёулаа - Excel-ээс импортлосон мэдээлэл'
    )
    import_ref = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Импортын лавлагаа',
        help_text='Excel импортын давхардлаас сэргийлэх лавлагаа'
    )

    # Дотоод хэрэгцээний зардлын журналын бичилт
    expense_accounting_entry = models.ForeignKey(
        'AccountingEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expense_sales',
        verbose_name='Зардлын журналын бичилт'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Үүсгэсэн огноо')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Шинэчилсэн огноо')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Үүсгэсэн хэрэглэгч'
    )
    
    class Meta:
        verbose_name = 'Борлуулалт'
        verbose_name_plural = 'Борлуулалтууд'
        ordering = ['-sale_date', '-created_at']
    
    def __str__(self):
        customer_name = self.customer.name if self.customer else "Бэлэн"
        return f"{self.sale_number} - {customer_name}"
    
    @property
    def remaining_amount(self):
        """Үлдэгдэл төлбөр"""
        return self.total_amount - self.paid_amount
    
    @property
    def is_fully_paid(self):
        """Бүрэн төлсөн эсэх"""
        return self.paid_amount >= self.total_amount
    
    def save(self, *args, **kwargs):
        """Хадгалахдаа дугаар автоматаар үүсгэх"""
        if not self.sale_number:
            # Огнооны формат: SAL-YYYYMMDD-XXX
            from datetime import datetime
            date_str = self.sale_date.strftime('%Y%m%d')
            
            # Өнөөдрийн сүүлийн дугаар олох
            last_sale = Sale.objects.filter(
                sale_number__startswith=f'SAL-{date_str}'
            ).order_by('-sale_number').first()
            
            if last_sale:
                # Сүүлийн дугаарыг задлах (SAL-20260209-001 → 001)
                last_num = int(last_sale.sale_number.split('-')[-1])
                next_num = last_num + 1
            else:
                next_num = 1
            
            self.sale_number = f'SAL-{date_str}-{next_num:03d}'
        
        super().save(*args, **kwargs)


class SaleItem(models.Model):
    """Борлуулалтын зүйл"""
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Борлуулалт'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name='Бүтээгдэхүүн'
    )
    quantity = models.IntegerField(verbose_name='Тоо ширхэг')
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Нэгж үнэ'
    )
    total_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Нийт үнэ',
        editable=False
    )
    
    class Meta:
        verbose_name = 'Борлуулалтын зүйл'
        verbose_name_plural = 'Борлуулалтын зүйлүүд'
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)


# ========================================
# SIGNALS - Журналын бичилт устах үед банкны гүйлгээг буцаах
# ========================================

from django.db.models.signals import pre_delete
from django.dispatch import receiver

@receiver(pre_delete, sender=AccountingEntry)
def reset_bank_transaction_on_entry_delete(sender, instance, **kwargs):
    """Журналын бичилт устах үед холбогдсон банкны гүйлгээ болон бүх хуваарилалтыг устгах."""
    # AccountingEntry.delete() override аль хэдийн хуваарилалтыг устгадаг тул
    # signal дотор давхардуулахгүй — зөвхөн нэмэлт аюулгүй байдлын log хийнэ.
    try:
        bank_transactions = BankTransaction.objects.filter(accounting_entry=instance)
        for bank_trans in bank_transactions:
            print(f"✓ Банкны гүйлгээ #{bank_trans.id} болон хуваарилалтууд нь устгагдах гэж байна (журнал устсан)")
    except Exception as e:
        print(f"⚠️ Signal алдаа: {str(e)}")


# ========================================
# САНХҮҮГИЙН ТОХИРГОО — Систем эхлэх огноо (эхний үлдэгдлийн огноо)
# ========================================

class FinanceSettings(models.Model):
    """Санхүү, бараа материалын бүртгэл шинээр эхэлсэн огноо (ганц мөртэй).

    books_start_date-ээс өмнөх гүйлгээ (банк, касс, журнал, борлуулалт, барааны
    хөдөлгөөн) архивд орж, жагсаалт болон үлдэгдлийн тооцоонд орохгүй. Үлдэгдэл =
    эхний үлдэгдэл (гараар оруулсан) + энэ огнооноос хойших гүйлгээ.
    """
    books_start_date = models.DateField(
        'Систем эхлэх огноо', null=True, blank=True,
        help_text='Энэ өдрөөс эхэлсэн гүйлгээ шинэ үед орно. Хоосон бол бүх гүйлгээ тооцогдоно.'
    )
    legacy_opening_snapshot = models.JSONField(
        'Хуучин эхний үлдэгдэл (нөөц)', default=dict, blank=True,
        help_text='Шинэ үе эхлэхэд тэглэсэн хуучин эхний үлдэгдлүүд'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'Санхүүгийн тохиргоо'
        verbose_name_plural = 'Санхүүгийн тохиргоо'

    def __str__(self):
        return f'Систем эхлэх огноо: {self.books_start_date or "—"}'

    def save(self, *args, **kwargs):
        self.pk = 1  # ганц мөр
        super().save(*args, **kwargs)
        from .books_period import clear_start_date_cache
        clear_start_date_cache()


# ========================================
# АВТОМАТ ХОЛБОЛТЫН ЗАГВАР — банкны гүйлгээг утгаар нь данс/үзүүлэлттэй холбох
# ========================================

class AutoLinkRule(models.Model):
    """Утга нь заасан үгийг агуулсан банкны гүйлгээг автоматаар холбох загвар."""
    DIRECTION_CHOICES = [
        ('EXPENSE', 'Зарлага'),
        ('INCOME', 'Орлого'),
        ('ANY', 'Аль аль нь'),
    ]

    name = models.CharField('Загварын нэр', max_length=100)
    keywords = models.TextField(
        'Түлхүүр үгс',
        help_text='Таслал эсвэл шинэ мөрөөр тусгаарлана. Аль нэг нь утга/харилцагчийн нэрэнд байвал таарна (том/жижиг үсэг ялгахгүй).'
    )
    direction = models.CharField('Чиглэл', max_length=10, choices=DIRECTION_CHOICES, default='EXPENSE')
    bank_account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
        verbose_name='Зөвхөн энэ банк', help_text='Хоосон бол бүх банк'
    )
    amount_min = models.DecimalField('Дүн (доод)', max_digits=15, decimal_places=2, null=True, blank=True)
    amount_max = models.DecimalField('Дүн (дээд)', max_digits=15, decimal_places=2, null=True, blank=True)

    offset_account = models.ForeignKey(
        ChartOfAccounts, on_delete=models.PROTECT, related_name='+', verbose_name='Эсрэг данс'
    )
    cash_flow_indicator = models.ForeignKey(
        'CashFlowIndicator', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
        verbose_name='Мөнгөн гүйлгээний үзүүлэлт'
    )
    income_type = models.CharField('Орлогын төрөл', max_length=50, blank=True)

    auto_apply = models.BooleanField(
        'Импортлох үед шууд холбох', default=False,
        help_text='Асаалттай бол хуулга импортлоход шалгалтгүйгээр холбогдоно (банкны шимтгэл гэх мэт найдвартай загварт).'
    )
    priority = models.PositiveIntegerField('Эрэмбэ', default=100, help_text='Бага тоо нь түрүүлж шалгагдана')
    is_active = models.BooleanField('Идэвхтэй', default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'id']
        verbose_name = 'Автомат холболтын загвар'
        verbose_name_plural = 'Автомат холболтын загварууд'

    def __str__(self):
        return self.name

    @property
    def keyword_list(self):
        import re
        return [k.strip().lower() for k in re.split(r'[,\n;]+', self.keywords or '') if k.strip()]

    def matches(self, tx):
        """Гүйлгээ энэ загварт таарах эсэх."""
        if self.direction == 'EXPENSE' and not tx.expense_amount > 0:
            return False
        if self.direction == 'INCOME' and not tx.income_amount > 0:
            return False
        if self.bank_account_id and tx.bank_account_id != self.bank_account_id:
            return False
        amount = tx.income_amount if tx.income_amount > 0 else tx.expense_amount
        if self.amount_min is not None and amount < self.amount_min:
            return False
        if self.amount_max is not None and amount > self.amount_max:
            return False
        text = f'{tx.description or ""} {tx.counterparty_name or ""}'.lower()
        return any(k in text for k in self.keyword_list)
