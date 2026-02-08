from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db.models.signals import post_save
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
    mongolian_name = models.CharField(max_length=200, verbose_name='Монгол нэр', blank=True)
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
        choices=[('M', 'Эрэгтэй'), ('F', 'Эмэгтэй')],
        verbose_name='Хүйс',
        blank=True
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
    notes = models.TextField(verbose_name='Тэмдэглэл', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Үүсгэсэн огноо')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Шинэчилсэн огноо')
    
    class Meta:
        verbose_name = 'Хэрэглэгчийн мэдээлэл'
        verbose_name_plural = 'Хэрэглэгчдийн мэдээлэл'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.mongolian_name or self.user.get_full_name() or self.user.username} ({self.get_role_display()})"
    
    @property
    def is_teacher(self):
        """Багш эсэхийг шалгах"""
        return self.role in [
            UserRole.TEACHER_BEGINNER,
            UserRole.TEACHER_INTERMEDIATE,
            UserRole.TEACHER_ADVANCED
        ]
    
    @property
    def is_admin(self):
        """Админ эрхтэй эсэхийг шалгах"""
        return self.role in [
            UserRole.PRESIDENT,
            UserRole.DIRECTOR,
            UserRole.MANAGER,
            UserRole.ACCOUNTANT
        ]
    
    @property
    def is_accountant(self):
        """Нягтлан бодогч эсэхийг шалгах"""
        return self.role == UserRole.ACCOUNTANT or self.is_admin
    
    @property
    def is_only_accountant(self):
        """Зөвхөн нягтлан бодогч эрхтэй эсэхийг шалгах (менежер биш)"""
        return self.role == UserRole.ACCOUNTANT
    
    @property
    def enrolled_courses_count(self):
        """Элссэн сургалтын тоо"""
        return self.enrollments.filter(is_active=True).count()


class Course(models.Model):
    """Сургалтын хичээл"""
    LEVEL_CHOICES = [
        ('BEGINNER', 'Анхан шат'),
        ('INTERMEDIATE', 'Дунд шат'),
        ('ADVANCED', 'Дээд шат'),
        ('VIP', 'VIP'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Нэр')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, verbose_name='Түвшин')
    description = models.TextField(verbose_name='Тайлбар', blank=True)
    duration_weeks = models.IntegerField(verbose_name='Үргэлжлэх хугацаа (долоо хоног)')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Үнэ (₮)')
    
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
    
    class Meta:
        ordering = ['-entry_date', '-entry_number']
        verbose_name = 'Гүйлгээний бичилт'
        verbose_name_plural = 'Гүйлгээний бичилтүүд'
    
    def __str__(self):
        return f"{self.entry_number} - {self.entry_date}"
    
    def save(self, *args, **kwargs):
        """Хадгалах үед дансуудын үлдэгдэл шинэчлэх"""
        is_new = self.pk is None
        
        if not is_new:
            # Хуучин утгыг буцаах
            old_entry = AccountingEntry.objects.get(pk=self.pk)
            old_entry.debit_account.debit_balance -= old_entry.debit_amount
            old_entry.debit_account.save()
            old_entry.credit_account.credit_balance -= old_entry.credit_amount
            old_entry.credit_account.save()
        
        super().save(*args, **kwargs)
        
        # Шинэ үлдэгдэл тооцох
        self.debit_account.debit_balance += self.debit_amount
        self.debit_account.save()
        
        self.credit_account.credit_balance += self.credit_amount
        self.credit_account.save()
    
    def delete(self, *args, **kwargs):
        """Устгах үед дансуудын үлдэгдлээс дүн хасах"""
        # Дебит дансны үлдэгдлээс хасах
        self.debit_account.debit_balance -= self.debit_amount
        self.debit_account.save()
        
        # Кредит дансны үлдэгдлээс хасах
        self.credit_account.credit_balance -= self.credit_amount
        self.credit_account.save()
        
        # Холбогдсон банкны гүйлгээний ангилал цэвэрлэх
        bank_transactions = BankTransaction.objects.filter(accounting_entry=self)
        for bank_tx in bank_transactions:
            # PaymentAllocation-ууд устгах
            bank_tx.allocations.all().delete()
            
            # Банкны гүйлгээний ангилал цэвэрлэх
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
    
    # Агуулах
    current_stock = models.IntegerField(default=0, verbose_name='Одоогийн үлдэгдэл')
    min_stock = models.IntegerField(default=0, verbose_name='Доод үлдэгдэл', help_text='Сануулга өгөх үлдэгдэл')
    
    # Зураг
    image = models.ImageField(
        upload_to='products/',
        null=True,
        blank=True,
        verbose_name='Зураг'
    )
    
    # Нийлүүлэгч
    supplier = models.CharField(max_length=200, blank=True, verbose_name='Нийлүүлэгч')
    supplier_contact = models.CharField(max_length=100, blank=True, verbose_name='Холбоо барих')
    
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
    
    # Холбогдох мэдээлэл
    reference_number = models.CharField(max_length=100, blank=True, verbose_name='Баримтын дугаар')
    customer_name = models.CharField(max_length=200, blank=True, verbose_name='Үйлчлүүлэгч/Нийлүүлэгч')
    
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
        # Нийт дүн тооцоолох
        self.total_amount = self.quantity * self.price
        
        # Агуулахын үлдэгдэл шинэчлэх
        if self.pk is None:  # Шинээр үүсгэж байгаа бол
            if self.movement_type == 'IN':
                self.product.current_stock += self.quantity
            elif self.movement_type in ['OUT', 'ADJUSTMENT']:
                self.product.current_stock -= self.quantity
            elif self.movement_type == 'RETURN':
                self.product.current_stock += self.quantity
            
            self.product.save()


# ========================================
# SIGNALS
# ========================================

@receiver(post_save, sender=UserProfile)
def update_user_staff_status(sender, instance, created, **kwargs):
    """
    Менежер эсвэл нягтлан эрхтэй хэрэглэгчдэд автоматаар staff статус өгөх
    """
    user = instance.user
    
    # Менежер, нягтлан нарт staff эрх өгөх (бараа материал удирдах эрхтэй)
    if instance.role in [UserRole.MANAGER, UserRole.ACCOUNTANT]:
        if not user.is_staff:
            user.is_staff = True
            user.save()
    
    # Админ эрхтэй бүх хүмүүст staff эрх өгөх
    elif instance.is_admin:
        if not user.is_staff:
            user.is_staff = True
            user.save()


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
    """Худалдан авалт"""
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
        verbose_name='Худалдан авалтын дугаар'
    )
    supplier = models.ForeignKey(
        Counterparty,
        on_delete=models.PROTECT,
        limit_choices_to={'counterparty_type__in': ['SUPPLIER', 'BOTH']},
        related_name='purchases',
        verbose_name='Нийлүүлэгч'
    )
    purchase_date = models.DateField(verbose_name='Огноо')
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
        return f"{self.purchase_number} - {self.supplier.name}"
    
    @property
    def remaining_amount(self):
        """Үлдэгдэл төлбөр"""
        return self.total_amount - self.paid_amount
    
    @property
    def is_fully_paid(self):
        """Бүрэн төлсөн эсэх"""
        return self.paid_amount >= self.total_amount


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
    """Журналын бичилт устах үед холбогдсон банкны гүйлгээг буцаах"""
    try:
        # Энэ журналын бичилттэй холбоотой банкны гүйлгээг хайх
        bank_transactions = BankTransaction.objects.filter(accounting_entry=instance)
        
        for bank_trans in bank_transactions:
            bank_trans.accounting_entry = None
            bank_trans.offset_account = None  # Эсрэг дансыг ч хоослох
            bank_trans.is_processed = False
            bank_trans.save()
            print(f"✓ Банкны гүйлгээ #{bank_trans.id} бүрэн буцаагдлаа (журнал устсан)")
    except Exception as e:
        print(f"⚠️ Банкны гүйлгээ буцаах алдаа: {str(e)}")
