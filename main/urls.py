from django.urls import path
from . import views

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
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/sheet/<int:course_id>/', views.attendance_sheet, name='attendance_sheet'),
    path('attendance/mark/<int:course_id>/', views.attendance_mark, name='attendance_mark'),
    path('student-payments/', views.student_payments, name='student_payments'),
    path('payment-comment/<int:transaction_id>/', views.update_payment_comment, name='update_payment_comment'),
    
    # Танилцуулга
    path('about/', views.about, name='about'),
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
    path('products/books/', views.books, name='books'),
    path('products/teacher-guidance/', views.teacher_guidance, name='teacher_guidance'),
    path('products/energy/', views.energy_products, name='energy_products'),
    path('products/bio-energy-diagnosis/', views.bio_energy_diagnosis, name='bio_energy_diagnosis'),
    
    # Аялал
    path('travel/', views.travel, name='travel'),
    
    # Холбоо барих
    path('contact/', views.contact, name='contact'),
    
    # Бараа материалын удирдлага
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/create/', views.product_create, name='product_create'),
    path('inventory/<int:product_id>/edit/', views.product_edit, name='product_edit'),
    path('inventory/stock-movement/', views.stock_movement_list, name='stock_movement_list'),
    path('inventory/stock-movement/create/', views.stock_movement_create, name='stock_movement_create'),
    
    # Санхүү, мөнгөн хөрөнгө
    path('finance/', views.finance_dashboard, name='finance_dashboard'),
    path('finance/opening-balance/', views.account_opening_balance, name='account_opening_balance'),
    path('finance/purchases/', views.purchase_list, name='purchase_list'),
    path('finance/sales/', views.sale_list, name='sale_list'),
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
    
    # AJAX API
    path('api/update-content/', views.update_page_content, name='update_page_content'),
]
