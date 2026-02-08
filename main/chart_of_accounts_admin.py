
# ========================================
# ДАНСНЫ ТӨЛӨВЛӨГӨӨ
# ========================================

@admin.register(ChartOfAccounts)
class ChartOfAccountsAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account_type', 'parent', 'debit_balance', 'credit_balance', 'balance_display', 'is_active')
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
            'fields': ('debit_balance', 'credit_balance', 'balance_display')
        }),
        ('Системийн мэдээлэл', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def balance_display(self, obj):
        return f"{obj.balance:,.2f}₮"
    balance_display.short_description = 'Үлдэгдэл'
    
    def has_add_permission(self, request):
        """Данс нэмэх эрхийг хаах - зөвхөн management команд ашиглана"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Данс устгах эрхийг хаах"""
        return False


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
    
    def has_add_permission(self, request):
        """Журналын бичилт нэмэх эрхийг хаах - зөвхөн журналын хуудаснаас нэмнэ"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Журналын бичилт устгах эрхийг хаах"""
        return False
