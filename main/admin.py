from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    UserProfile, Course, Enrollment, Attendance, UserRole, PageContent,
    ProductCategory, Product, StockMovement,
    Account, Counterparty, Transaction, Purchase, PurchaseItem, Sale, SaleItem,
    ChartOfAccounts, AccountingEntry, BankTransaction, CashFlowIndicator, PaymentAllocation
)

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Хэрэглэгчийн мэдээлэл'
    fields = (
        'role', 'mongolian_name', 'phone', 'birth_date', 'gender',
        'address', 'city', 'district',
        'enrollment_date', 'is_active_student', 'photo', 'notes'
    )

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'get_mongolian_name', 'get_phone', 'email', 'get_role', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__role')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'profile__mongolian_name', 'profile__phone')
    
    def get_mongolian_name(self, obj):
        if hasattr(obj, 'profile') and obj.profile.mongolian_name:
            return obj.profile.mongolian_name
        return '-'
    get_mongolian_name.short_description = 'Монгол нэр'
    
    def get_phone(self, obj):
        if hasattr(obj, 'profile') and obj.profile.phone:
            return obj.profile.phone
        return '-'
    get_phone.short_description = 'Утас'
    
    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return '-'
    get_role.short_description = 'Эрх'

# Unregister the original User admin
admin.site.unregister(User)
# Register the new User admin
admin.site.register(User, UserAdmin)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('mongolian_name', 'user', 'role', 'phone', 'city', 'is_active_student', 'created_at')
    list_filter = ('role', 'is_active_student', 'gender', 'city')
    search_fields = ('mongolian_name', 'user__username', 'user__email', 'phone')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Хэрэглэгч', {
            'fields': ('user', 'role')
        }),
        ('Хувийн мэдээлэл', {
            'fields': ('mongolian_name', 'phone', 'birth_date', 'gender', 'photo')
        }),
        ('Хаяг', {
            'fields': ('address', 'city', 'district')
        }),
        ('Сургалт', {
            'fields': ('enrollment_date', 'is_active_student')
        }),
        ('Нэмэлт', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'teacher', 'start_date', 'end_date', 'enrolled_count', 'max_students', 'is_active')
    list_filter = ('level', 'is_active', 'start_date')
    search_fields = ('name', 'description', 'teacher__mongolian_name')
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Үндсэн мэдээлэл', {
            'fields': ('name', 'level', 'description', 'price')
        }),
        ('Хугацаа', {
            'fields': ('duration_weeks', 'start_date', 'end_date')
        }),
        ('Багш болон багтаамж', {
            'fields': ('teacher', 'max_students', 'is_active')
        }),
    )
    
    def enrolled_count(self, obj):
        return obj.enrolled_count
    enrolled_count.short_description = 'Элссэн тоо'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('teacher', 'teacher__user')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrolled_date', 'status', 'is_paid', 'payment_amount', 'certificate_issued')
    list_filter = ('status', 'is_paid', 'certificate_issued', 'enrolled_date', 'course__level')
    search_fields = ('student__mongolian_name', 'course__name', 'student__user__username')
    date_hierarchy = 'enrolled_date'
    
    fieldsets = (
        ('Бүртгэл', {
            'fields': ('student', 'course', 'status', 'is_active')
        }),
        ('Төлбөр', {
            'fields': ('payment_amount', 'payment_date', 'is_paid')
        }),
        ('Гэрчилгээ', {
            'fields': ('certificate_issued', 'certificate_date')
        }),
        ('Тэмдэглэл', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_paid', 'mark_as_approved', 'issue_certificate']
    
    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(is_paid=True, payment_date=timezone.now().date())
        self.message_user(request, f'{updated} бүртгэлийг төлсөн гэж тэмдэглэлээ.')
    mark_as_paid.short_description = 'Төлбөр төлсөн гэж тэмдэглэх'
    
    def mark_as_approved(self, request, queryset):
        updated = queryset.update(status='APPROVED')
        self.message_user(request, f'{updated} бүртгэлийг баталлаа.')
    mark_as_approved.short_description = 'Баталсан гэж тэмдэглэх'
    
    def issue_certificate(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(certificate_issued=True, certificate_date=timezone.now().date())
        self.message_user(request, f'{updated} сурагчид гэрчилгээ олгосон.')
    issue_certificate.short_description = 'Гэрчилгээ олгох'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('student', 'student__user', 'course')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'date', 'present', 'notes')
    list_filter = ('present', 'date', 'enrollment__course')
    search_fields = ('enrollment__student__mongolian_name', 'enrollment__course__name')
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('enrollment', 'enrollment__student', 'enrollment__course')

@admin.register(PageContent)
class PageContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'key', 'page', 'is_active', 'updated_at', 'updated_by')
    list_filter = ('page', 'is_active', 'updated_at')
    search_fields = ('title', 'key', 'content')
    readonly_fields = ('updated_at', 'updated_by')
    
    fieldsets = (
        ('Үндсэн мэдээлэл', {
            'fields': ('key', 'title', 'page', 'is_active')
        }),
        ('Агуулга', {
            'fields': ('content',),
            'description': 'Вэб дээр харагдах текстийг энд засна. HTML тэмдэглэгээ ашиглаж болно.',
        }),
        ('Бусад', {
            'fields': ('updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    def has_module_permission(self, request):
        """
        Content Editor бүлэгт харьяалагдаж байвал харуулна
        """
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name='Content Editor').exists() or \
               request.user.has_perm('main.view_pagecontent')

# Admin site customization
admin.site.site_header = 'Готопа бясалгалын төв - Удирдлага'
admin.site.site_title = 'Готопа админ'
admin.site.index_title = 'Удирдлагын систем'


# ========================================
# БАРАА МАТЕРИАЛЫН УДИРДЛАГА
# ========================================

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active', 'product_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    
    fieldsets = (
        ('Үндсэн мэдээлэл', {
            'fields': ('name', 'parent', 'description', 'is_active')
        }),
    )
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Бүтээгдэхүүний тоо'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'name', 'category', 'purchase_price', 'selling_price',
        'current_stock', 'stock_status', 'is_active', 'created_at'
    )
    list_filter = ('category', 'is_active', 'unit', 'created_at')
    search_fields = ('code', 'name', 'supplier', 'description')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'profit_margin', 'stock_value')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Үндсэн мэдээлэл', {
            'fields': ('code', 'name', 'category', 'description', 'image')
        }),
        ('Үнэ ба ашиг', {
            'fields': ('purchase_price', 'selling_price', 'profit_margin', 'unit')
        }),
        ('Агуулах', {
            'fields': ('current_stock', 'min_stock', 'stock_value')
        }),
        ('Нийлүүлэгч', {
            'fields': ('supplier', 'supplier_contact'),
            'classes': ('collapse',)
        }),
        ('Бусад', {
            'fields': ('is_active', 'notes', 'created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_active', 'mark_as_inactive', 'check_low_stock']
    
    def stock_status(self, obj):
        if obj.is_low_stock:
            return f'⚠️ БАГ ({obj.current_stock})'
        return f'✓ {obj.current_stock}'
    stock_status.short_description = 'Үлдэгдэл'
    
    def profit_margin(self, obj):
        return f'{obj.profit_margin:.1f}%'
    profit_margin.short_description = 'Ашгийн хувь'
    
    def stock_value(self, obj):
        return f'{obj.stock_value:,.0f}₮'
    stock_value.short_description = 'Үлдэгдлийн үнэ'
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} бүтээгдэхүүнийг идэвхжүүллээ.')
    mark_as_active.short_description = 'Идэвхжүүлэх'
    
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} бүтээгдэхүүнийг идэвхгүй болголоо.')
    mark_as_inactive.short_description = 'Идэвхгүй болгох'
    
    def check_low_stock(self, request, queryset):
        low_stock = [p for p in queryset if p.is_low_stock]
        self.message_user(
            request,
            f'Үлдэгдэл бага бүтээгдэхүүн: {len(low_stock)} / {queryset.count()}'
        )
    check_low_stock.short_description = 'Үлдэгдэл бага эсэхийг шалгах'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Шинэ бүтээгдэхүүн үүсгэж байгаа бол
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('category', 'created_by')


class StockMovementInline(admin.TabularInline):
    model = StockMovement
    extra = 0
    readonly_fields = ('total_amount', 'created_at', 'created_by')
    fields = ('movement_type', 'quantity', 'price', 'total_amount', 'reference_number', 'created_at')
    can_delete = False


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        'created_at', 'product', 'movement_type', 'quantity',
        'price', 'total_amount', 'customer_name', 'created_by'
    )
    list_filter = ('movement_type', 'created_at', 'product__category')
    search_fields = ('product__name', 'product__code', 'reference_number', 'customer_name')
    readonly_fields = ('total_amount', 'created_at', 'created_by')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Бүтээгдэхүүн ба төрөл', {
            'fields': ('product', 'movement_type')
        }),
        ('Тоо хэмжээ ба үнэ', {
            'fields': ('quantity', 'price', 'total_amount')
        }),
        ('Холбогдох мэдээлэл', {
            'fields': ('reference_number', 'customer_name', 'notes')
        }),
        ('Системийн мэдээлэл', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product', 'created_by')
    
    def has_delete_permission(self, request, obj=None):
        # Агуулахын хөдөлгөөнийг устгахыг хориглох (санхүүгийн аюулгүй байдлын үүднээс)
        return request.user.is_superuser


# ========================================
# САНХҮҮГИЙН МОДУЛУУД
# ========================================

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'account_type', 'balance', 'bank_name', 'is_active', 'updated_at')
    list_filter = ('account_type', 'is_active', 'created_at')
    search_fields = ('name', 'account_number', 'bank_name')
    readonly_fields = ('balance', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Үндсэн мэдээлэл', {
            'fields': ('name', 'account_type', 'is_active')
        }),
        ('Банкны мэдээлэл', {
            'fields': ('bank_name', 'account_number'),
            'classes': ('collapse',)
        }),
        ('Үлдэгдэл', {
            'fields': ('balance',),
            'description': 'Үлдэгдэл нь гүйлгээнүүдээр автоматаар өөрчлөгдөнө'
        }),
        ('Нэмэлт', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Counterparty)
class CounterpartyAdmin(admin.ModelAdmin):
    list_display = ('name', 'counterparty_type', 'phone', 'email', 'balance', 'is_active')
    list_filter = ('counterparty_type', 'is_active', 'created_at')
    search_fields = ('name', 'phone', 'email', 'registration_number')
    readonly_fields = ('balance', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Үндсэн мэдээлэл', {
            'fields': ('name', 'counterparty_type', 'is_active')
        }),
        ('Холбоо барих', {
            'fields': ('contact_person', 'phone', 'email', 'address')
        }),
        ('Регистр', {
            'fields': ('registration_number', 'tax_number'),
            'classes': ('collapse',)
        }),
        ('Тооцоо', {
            'fields': ('balance',),
            'description': 'Эерэг = Манай өр, Сөрөг = Тэдний өр'
        }),
        ('Нэмэлт', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_date', 'transaction_type', 'amount', 'account',
        'counterparty', 'description', 'created_by'
    )
    list_filter = ('transaction_type', 'transaction_date', 'account')
    search_fields = ('description', 'reference_number', 'counterparty__name')
    readonly_fields = ('created_at', 'created_by')
    date_hierarchy = 'transaction_date'
    
    fieldsets = (
        ('Гүйлгээний мэдээлэл', {
            'fields': ('transaction_type', 'transaction_date', 'amount')
        }),
        ('Данс', {
            'fields': ('account', 'to_account'),
            'description': 'Шилжүүлэг бол "Хүлээн авах данс"-ыг сонгоно'
        }),
        ('Харилцагч', {
            'fields': ('counterparty', 'description', 'reference_number')
        }),
        ('Холбогдох бүртгэл', {
            'fields': ('related_purchase', 'related_sale'),
            'classes': ('collapse',)
        }),
        ('Нэмэлт', {
            'fields': ('notes', 'created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1
    fields = ('product', 'quantity', 'unit_price', 'total_price')
    readonly_fields = ('total_price',)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        'purchase_number', 'supplier', 'purchase_date', 'total_amount',
        'paid_amount', 'remaining_amount', 'status', 'created_by'
    )
    list_filter = ('status', 'purchase_date', 'payment_account')
    search_fields = ('purchase_number', 'supplier__name')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'remaining_amount')
    date_hierarchy = 'purchase_date'
    inlines = [PurchaseItemInline]
    
    fieldsets = (
        ('Үндсэн мэдээлэл', {
            'fields': ('purchase_number', 'supplier', 'purchase_date', 'status')
        }),
        ('Үнийн мэдээлэл', {
            'fields': ('total_amount', 'paid_amount', 'remaining_amount')
        }),
        ('Төлбөр', {
            'fields': ('payment_account', 'payment_date')
        }),
        ('Нэмэлт', {
            'fields': ('notes', 'created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1
    fields = ('product', 'quantity', 'unit_price', 'total_price')
    readonly_fields = ('total_price',)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        'sale_number', 'customer', 'sale_date', 'total_amount',
        'paid_amount', 'remaining_amount', 'status', 'created_by'
    )
    list_filter = ('status', 'sale_date', 'payment_account')
    search_fields = ('sale_number', 'customer__name')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'remaining_amount')
    date_hierarchy = 'sale_date'
    inlines = [SaleItemInline]
    
    fieldsets = (
        ('Үндсэн мэдээлэл', {
            'fields': ('sale_number', 'customer', 'sale_date', 'status')
        }),
        ('Үнийн мэдээлэл', {
            'fields': ('total_amount', 'paid_amount', 'remaining_amount')
        }),
        ('Төлбөр', {
            'fields': ('payment_account', 'payment_date')
        }),
        ('Нэмэлт', {
            'fields': ('notes', 'created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)





# ========================================
# ========================================
# ДАНСНЫ ТӨЛӨВЛӨГӨӨ
# ========================================

@admin.register(ChartOfAccounts)
class ChartOfAccountsAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account_type', 'parent', 'opening_balance', 'debit_balance', 'credit_balance', 'balance_display', 'is_active')
    list_filter = ('account_type', 'is_active')
    search_fields = ('code', 'name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'balance_display')
    ordering = ('code',)
    
    fieldsets = (
        ('Үндсэн мэдээлэл', {
            'fields': ('code', 'name', 'account_type', 'parent', 'is_active')
        }),
        ('Тайлбар', {
            'fields': ('description',)
        }),
        ('Үлдэгдэл', {
            'fields': ('opening_balance', 'debit_balance', 'credit_balance', 'balance_display')
        }),
        ('Системийн мэдээлэл', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def balance_display(self, obj):
        return f"{obj.balance:,.2f}₮"
    balance_display.short_description = 'Үлдэгдэл'


@admin.register(AccountingEntry)
class AccountingEntryAdmin(admin.ModelAdmin):
    list_display = ('entry_number', 'entry_date', 'debit_account', 'debit_amount', 
                    'credit_account', 'credit_amount', 'description_short', 'created_by')
    list_filter = ('entry_date', 'created_by')
    search_fields = ('entry_number', 'description', 'debit_account__name', 'credit_account__name')
    readonly_fields = ('created_at', 'created_by')
    date_hierarchy = 'entry_date'
    
    fieldsets = (
        ('Гүйлгээний мэдээлэл', {
            'fields': ('entry_number', 'entry_date', 'description')
        }),
        ('Дебит', {
            'fields': ('debit_account', 'debit_amount')
        }),
        ('Кредит', {
            'fields': ('credit_account', 'credit_amount')
        }),
        ('Системийн мэдээлэл', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Тайлбар'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def delete_model(self, request, obj):
        """Журналын бичилт устгах үед мессаж харуулах"""
        from main.models import BankTransaction
        
        # Холбоотой банкны гүйлгээ шалгах
        bank_trans = BankTransaction.objects.filter(accounting_entry=obj)
        count = bank_trans.count()
        
        # Устгах (signal автоматаар банкны гүйлгээг буцаана)
        super().delete_model(request, obj)
        
        if count > 0:
            self.message_user(
                request,
                f'Журналын бичилт устгагдаж, холбоотой {count} банкны гүйлгээ буцаагдлаа.',
                level='WARNING'
            )
    
    def delete_queryset(self, request, queryset):
        """Олон журналын бичилт устгах үед"""
        from main.models import BankTransaction
        
        count = 0
        for obj in queryset:
            count += BankTransaction.objects.filter(accounting_entry=obj).count()
        
        # Устгах (signal автоматаар банкны гүйлгээг буцаана)
        super().delete_queryset(request, queryset)
        
        if count > 0:
            self.message_user(
                request,
                f'{queryset.count()} журналын бичилт устгагдаж, {count} банкны гүйлгээ буцаагдлаа.',
                level='WARNING'
            )


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'account_type', 'bank_name', 'bank_account', 'description_short',
                    'income_amount', 'expense_amount', 'offset_account', 'is_processed', 'imported_at')
    list_filter = ('account_type', 'bank_name', 'bank_account', 'is_processed', 'transaction_date', 'offset_account')
    search_fields = ('description', 'counterparty_name', 'counterparty_account')
    readonly_fields = ('imported_at', 'imported_by', 'accounting_entry', 'bank_name')
    date_hierarchy = 'transaction_date'
    list_per_page = 100  # Нэг хуудсанд 100 гүйлгээ харуулах (default: 100)
    
    fieldsets = (
        ('Банкны мэдээлэл', {
            'fields': ('bank_name', 'bank_account', 'transaction_date', 'transaction_time')
        }),
        ('Гүйлгээний утга', {
            'fields': ('description', 'counterparty_name', 'counterparty', 'counterparty_account')
        }),
        ('Дүнгүүд', {
            'fields': ('income_amount', 'expense_amount', 'opening_balance', 'closing_balance')
        }),
        ('⭐ ЭСРЭГ ДАНС (Заавал холбох!)', {
            'fields': ('offset_account',),
            'classes': ('wide',),
            'description': '💡 Орлого бол кредит дансыг (4xxx), зарлага бол дебит дансыг (5xxx) сонгоно уу'
        }),
        ('Системийн мэдээлэл', {
            'fields': ('accounting_entry', 'is_processed', 'imported_at', 'imported_by', 'branch_code'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['regenerate_journal_entries']
    
    def regenerate_journal_entries(self, request, queryset):
        """Эсрэг данс холбосон гүйлгээнүүдийг дахин журналд оруулах"""
        from main.import_bank_transactions import regenerate_accounting_entries
        count = regenerate_accounting_entries(queryset, request.user)
        self.message_user(request, f'{count} гүйлгээний журналын бичилт шинэчлэгдлээ.')
    regenerate_journal_entries.short_description = '✅ Эсрэг данс холбоод журналд дахин оруулах'
    
    fieldsets = (
        ('Банкны мэдээлэл', {
            'fields': ('bank_name', 'bank_account', 'transaction_date', 'transaction_time')
        }),
        ('Гүйлгээний мэдээлэл', {
            'fields': ('description', 'income_amount', 'expense_amount')
        }),
        ('Харилцагч', {
            'fields': ('counterparty', 'counterparty_name', 'counterparty_account')
        }),
        ('Үлдэгдэл', {
            'fields': ('opening_balance', 'closing_balance'),
            'classes': ('collapse',)
        }),
        ('Бусад', {
            'fields': ('branch_code', 'exchange_rate'),
            'classes': ('collapse',)
        }),
        ('Систем', {
            'fields': ('is_processed', 'accounting_entry', 'imported_by', 'imported_at'),
            'classes': ('collapse',)
        }),
    )
    
    def description_short(self, obj):
        return obj.description[:40] + '...' if len(obj.description) > 40 else obj.description
    description_short.short_description = 'Утга'
    
    def save_model(self, request, obj, form, change):
        if not change and not obj.imported_by:
            obj.imported_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CashFlowIndicator)
class CashFlowIndicatorAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'flow_type', 'level', 'is_active', 'parent')
    list_filter = ('flow_type', 'level', 'is_active')
    search_fields = ('code', 'name')
    list_editable = ('is_active',)
    ordering = ('code',)
    
    fieldsets = (
        ('Үндсэн мэдээлэл', {
            'fields': ('code', 'name', 'flow_type', 'level')
        }),
        ('Бүтэц', {
            'fields': ('parent', 'sort_order')
        }),
        ('Төлөв', {
            'fields': ('is_active',)
        }),
    )

@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'student_name', 'course', 'year', 'month', 'amount', 'created_at')
    list_filter = ('year', 'month', 'course')
    search_fields = ('student__mongolian_name', 'student__user__username', 'transaction__description', 'comment')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Гүйлгээ', {
            'fields': ('transaction',)
        }),
        ('Төлбөрийн мэдээлэл', {
            'fields': ('student', 'course', 'year', 'month', 'amount')
        }),
        ('Нэмэлт', {
            'fields': ('comment', 'color'),
            'classes': ('collapse',)
        }),
    )
    
    def student_name(self, obj):
        return obj.student.mongolian_name or obj.student.user.username
    student_name.short_description = 'Сурагч'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('transaction', 'student', 'student__user', 'course')