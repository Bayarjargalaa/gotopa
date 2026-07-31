from django.urls import path
from . import views
from .views_permissions import (
    permission_group_list, 
    permission_group_create, 
    permission_group_edit,
    permission_group_delete,
    user_groups_edit
)

app_name = 'main'

urlpatterns = [
    path('', views.home, name='home'),
    
    # Authentication
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    
    # Management
    path('students/', views.student_list, name='student_list'),
    path('students/create/', views.student_create, name='student_create'),
    path('students/<int:student_id>/edit/', views.student_update, name='student_update'),
    path('students/<int:student_id>/delete/', views.student_delete, name='student_delete'),
    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/create/', views.teacher_create, name='teacher_create'),
    path('teachers/<int:teacher_id>/edit/', views.teacher_update, name='teacher_update'),
    path('teachers/<int:teacher_id>/delete/', views.teacher_delete, name='teacher_delete'),
    path('course-list/', views.course_list, name='course_list'),
    path('course/create/', views.course_create, name='course_create'),
    path('course/<int:course_id>/edit/', views.course_edit, name='course_edit'),
    path('course/<int:course_id>/delete/', views.course_delete, name='course_delete'),
    path('enrollments/', views.enrollment_list, name='enrollment_list'),
    path('enrollments/<int:enrollment_id>/approve/', views.enrollment_approve, name='enrollment_approve'),
    path('enrollments/<int:enrollment_id>/reject/', views.enrollment_reject, name='enrollment_reject'),
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/sheet/<int:course_id>/', views.attendance_sheet, name='attendance_sheet'),
    path('attendance/mark/<int:course_id>/', views.attendance_mark, name='attendance_mark'),
    path('student-payments/', views.student_payments, name='student_payments'),
    path('payment-comment/<int:transaction_id>/', views.update_payment_comment, name='update_payment_comment'),
    
    # Танилцуулга
    path('about/', views.about, name='about'),
    path('about/vision/', views.vision, name='vision'),    
    path('about/leadership/', views.leadership, name='leadership'),
    path('ethics/', views.ethics, name='ethics'),
    path('gotopa-meditation/', views.gotopa_meditation, name='gotopa_meditation'),
    path('guru-gotopa/', views.guru_gotopa, name='guru_gotopa'),
    path('meditation-center/', views.meditation_center, name='meditation_center'),
    
    # Мэдээлэл
    path('news/', views.news, name='news'),
    
    # Бясалгалын сургалтууд
    path('courses/', views.courses, name='courses'),
    path('courses/beginner/', views.beginner_meditation, name='beginner_meditation'),
    path('courses/intermediate/', views.intermediate_meditation, name='intermediate_meditation'),
    path('courses/advanced/', views.advanced_meditation, name='advanced_meditation'),
    path('courses/vip/', views.vip_meditation, name='vip_meditation'),
    
    # Бүтээгдэхүүн
    path('products/', views.products, name='products'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('products/books/', views.books, name='books'),
    path('products/teacher-guidance/', views.teacher_guidance, name='teacher_guidance'),
    path('products/energy/', views.energy_products, name='energy_products'),
    path('products/bio-energy-diagnosis/', views.bio_energy_diagnosis, name='bio_energy_diagnosis'),
    
    # Аялал
    path('travel/', views.travel, name='travel'),
    
    # Холбоо барих
    path('contact/', views.contact, name='contact'),
    # Галерей
    path('gallery/', views.gallery, name='gallery'),
    # Хандив
    path('donate/', views.donate, name='donate'),
    
    # Бараа материалын удирдлага
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/set-initial-stock/', views.product_set_initial_stock, name='product_set_initial_stock'),
    path('inventory/create/', views.product_create, name='product_create'),
    path('inventory/<int:product_id>/edit/', views.product_edit, name='product_edit'),
    path('inventory/stock-movement/', views.stock_movement_list, name='stock_movement_list'),
    path('inventory/stock-movement/create/', views.stock_movement_create, name='stock_movement_create'),
    path('inventory/free-intake/', views.stock_free_intake, name='stock_free_intake'),
    path('inventory/free-outgoing/', views.stock_free_outgoing, name='stock_free_outgoing'),
    path('inventory/purchase/', views.purchase_create, name='purchase_create'),
    path('inventory/purchase/multi/', views.purchase_create_multi, name='purchase_create_multi'),
    path('inventory/purchase/<int:movement_id>/edit/', views.purchase_edit, name='purchase_edit'),
    path('inventory/purchase/<int:movement_id>/delete/', views.purchase_delete, name='purchase_delete'),
    path('inventory/sale/', views.sale_create, name='sale_create'),
    path('inventory/sale/multi/', views.sale_create_multi, name='sale_create_multi'),
    path('inventory/sale/<int:movement_id>/edit/', views.sale_edit, name='sale_edit'),
    path('inventory/sale/<int:movement_id>/delete/', views.sale_delete, name='sale_delete'),
    
    # Санхүү, мөнгөн хөрөнгө
    path('finance/', views.finance_dashboard, name='finance_dashboard'),
    path('finance/opening-balance/', views.account_opening_balance, name='account_opening_balance'),
    path('finance/purchases/', views.purchase_list, name='purchase_list'),
    path('finance/sales/', views.sale_list, name='sale_list'),
    path('finance/sales/<int:sale_id>/', views.sale_detail, name='sale_detail'),
    path('finance/sales/<int:sale_id>/edit/', views.sale_finance_edit, name='sale_finance_edit'),
    path('finance/sales/<int:sale_id>/delete/', views.sale_finance_delete, name='sale_finance_delete'),
    path('finance/sales/<int:sale_id>/link-bank/', views.sale_link_bank, name='sale_link_bank'),
    path('finance/transactions/', views.transaction_list, name='transaction_list'),
    path('finance/import-counterparties/', views.import_counterparties_view, name='import_counterparties'),
    path('finance/import-bank-transactions/', views.import_bank_transactions_view, name='import_bank_transactions'),
    path('finance/bank-transactions/', views.bank_transaction_list, name='bank_transaction_list'),
    path('finance/bank-transactions/<int:transaction_id>/link-to-journal/', views.link_bank_transaction_to_journal, name='link_bank_transaction_to_journal'),
    path('api/bank-accounts/', views.get_bank_accounts_api, name='get_bank_accounts_api'),
    path('api/student-courses/<int:student_id>/', views.get_student_courses, name='get_student_courses'),
    
    # Кассын бүртгэл
    path('finance/cash-transactions/', views.cash_transaction_list, name='cash_transaction_list'),
    path('finance/cash-transactions/create/', views.cash_transaction_create, name='cash_transaction_create'),
    path('finance/cash-transactions/<int:transaction_id>/edit/', views.cash_transaction_edit, name='cash_transaction_edit'),
    path('finance/cash-transactions/<int:transaction_id>/delete/', views.cash_transaction_delete, name='cash_transaction_delete'),
    
    # Ерөнхий журнал
    path('finance/journal/', views.journal_list, name='journal_list'),
    path('finance/journal/create/', views.journal_create, name='journal_create'),
    path('finance/journal/<int:entry_id>/delete/', views.journal_delete, name='journal_delete'),
    
    # Дансны төлөвлөгөө
    path('finance/chart-of-accounts/', views.chart_of_accounts_list, name='chart_of_accounts_list'),
    path('finance/chart-of-accounts/create/', views.chart_account_create, name='chart_account_create'),
    path('finance/chart-of-accounts/<int:account_id>/edit/', views.chart_account_edit, name='chart_account_edit'),
    path('finance/chart-of-accounts/<int:account_id>/delete/', views.chart_account_delete, name='chart_account_delete'),
    
    # Барааны тайлан
    path('reports/inventory-summary-quantity/', views.inventory_summary_quantity, name='inventory_summary_quantity'),
    path('reports/inventory-summary-sales/', views.inventory_summary_sales, name='inventory_summary_sales'),
    path('reports/inventory-summary-purchases/', views.inventory_summary_purchases, name='inventory_summary_purchases'),
    path('reports/inventory-balance/', views.inventory_balance_report, name='inventory_balance_report'),
    path('reports/bank-statement/', views.bank_statement_report, name='bank_statement_report'),
    
    # Харилцагч удирдлага
    path('counterparties/', views.counterparty_list, name='counterparty_list'),
    path('counterparties/create/', views.counterparty_create, name='counterparty_create'),
    path('counterparties/<int:counterparty_id>/edit/', views.counterparty_edit, name='counterparty_edit'),
    path('counterparties/<int:counterparty_id>/delete/', views.counterparty_delete, name='counterparty_delete'),
    
    # Хэрэглэгчийн удирдлага (HTML интерфэйс)
    path('users/', views.user_management, name='user_management'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    
    # Бүлгийн удирдлага (HTML интерфэйс)
    path('groups/', views.group_list, name='group_list'),
    path('groups/create/', views.group_create, name='group_create'),
    path('groups/<int:group_id>/edit/', views.group_edit, name='group_edit'),
    path('groups/<int:group_id>/delete/', views.group_delete, name='group_delete'),
    
    # Роль-ын мэдээлэл
    path('roles/', views.role_info, name='role_info'),
    
    # Эрхийн удирдлага (Permission Management)
    path('permissions/groups/', permission_group_list, name='permission_group_list'),
    path('permissions/groups/create/', permission_group_create, name='permission_group_create'),
    path('permissions/groups/<int:group_id>/edit/', permission_group_edit, name='permission_group_edit'),
    path('permissions/groups/<int:group_id>/delete/', permission_group_delete, name='permission_group_delete'),
    path('permissions/users/<int:user_id>/groups/', user_groups_edit, name='user_groups_edit'),
    
    # AJAX API
    path('api/update-content/', views.update_page_content, name='update_page_content'),
]
