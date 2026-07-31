"""
Цэсний тохиргоо - эрхээр шүүж харуулах
"""

# Header Navigation (Public + Private)
# Загварын дагуу 9 цэс: Эхлэл · Бидний тухай · Сургалтын хөтөлбөрүүд · Бясалгал · Багш нар · Мэдээ, мэдээлэл · Галерей · Хандив · Холбоо барих
HEADER_MENU = [
    {
        'label': 'Эхлэл',
        'url_name': 'main:home',
        'permissions': [],
    },
    {
        'label': 'Бидний тухай',
        'is_dropdown': True,
        'permissions': [],
        'items': [
            {
                'label': 'Бидний тухай',
                'url_name': 'main:about',
            },
            {
                'label': 'Гүрү Готопа',
                'url_name': 'main:guru_gotopa',
            },
            {
                'label': 'Алсын хараа, Эрхэм зорилго',
                'url_name': 'main:vision',
            },
            {
                'label': 'Удирдлага',
                'url_name': 'main:leadership',
            },
            {
                'label': 'Ёс зүйн дүрэм',
                'url_name': 'main:ethics',
            },
        ]
    },
    {
        'label': 'Бүтээгдэхүүн',
        'url_name': 'main:products',
        'permissions': [],
    },
    {
        'label': 'Бясалгал',
        'is_dropdown': True,
        'permissions': [],
        'items': [
            {
                'label': 'Анхан шат',
                'url_name': 'main:beginner_meditation',
            },
            {
                'label': 'Дунд шат',
                'url_name': 'main:courses',
            },
            {
                'label': 'Ахисан шат',
                'url_name': 'main:courses',
            },
            {
                'label': 'Багшийн анги',
                'url_name': 'main:vip_meditation',
            },
        ]
    },
    {
        'label': 'Багш нар',
        'url_name': 'main:teacher_list',
        'permissions': [],
    },
    {
        'label': 'Мэдээ, мэдээлэл',
        'url_name': 'main:news',
        'permissions': [],
    },
    {
        'label': 'Галерей',
        'url_name': 'main:gallery',
        'permissions': [],
    },
    {
        'label': 'Хандив',
        'url_name': 'main:donate',
        'permissions': [],
    },
    {
        'label': 'Холбоо барих',
        'url_name': 'main:contact',
        'permissions': [],
    },
]

# Sidebar цэс (Dashboard sidebar)
SIDEBAR_MENU = [
    {
        'section': 'Хувийн',
        'icon': 'fas fa-user-circle',
        'permissions': ['authenticated'],  # Нэвтэрсэн бүх хэрэглэгч
        'items': [
            {
                'label': 'Dashboard',
                'url_name': 'main:dashboard',
                'icon': 'fas fa-th-large',
                'permissions': ['authenticated'],
            },
            {
                'label': 'Миний мэдээлэл',
                'url_name': 'main:profile',
                'icon': 'fas fa-user',
                'permissions': ['authenticated'],
            },
        ]
    },
    {
        'section': 'Санхүү',
        'icon': 'fas fa-coins',
        'permissions': [],  # Хоосон = item-үүдийн эрхээр шүүгдэнэ
        'items': [
            {
                'label': 'Санхүүгийн хяналт',
                'url_name': 'main:finance_dashboard',
                'icon': 'fas fa-chart-line',
                'permissions': ['is_admin', 'is_accountant'],  # Зөвхөн админ, нягтлан - permission-based хасагдсан
            },
            {
                'label': 'Журнал',
                'url_name': 'main:journal_list',
                'icon': 'fas fa-book',
                'permissions': ['is_admin', 'is_manager', 'is_accountant'],  # Менежер харна, permission-based хасагдсан
            },
            {
                'label': 'Дансны төлөвлөгөө',
                'url_name': 'main:chart_of_accounts_list',
                'icon': 'fas fa-list-alt',
                'permissions': ['is_admin', 'is_accountant'],  # Permission-based хасагдсан
            },
            {
                'label': 'Банкны хуулга оруулах',
                'url_name': 'main:import_bank_transactions',
                'icon': 'fas fa-file-import',
                'permissions': ['is_admin', 'is_accountant'],  # Permission-based хасагдсан
            },
            {
                'label': 'Банкны гүйлгээ',
                'url_name': 'main:bank_transaction_list',
                'icon': 'fas fa-list',
                'permissions': ['is_admin', 'is_manager', 'is_accountant'],  # Менежер нэмэгдсэн
            },
            {
                'label': 'Кассын бүртгэл',
                'url_name': 'main:cash_transaction_list',
                'icon': 'fas fa-money-bill-wave',
                'permissions': ['is_admin', 'is_manager', 'is_accountant'],  # Менежер нэмэгдсэн
            },
        ]
    },
    {
        'section': '📦 Бараа материал',
        'icon': 'fas fa-boxes',
        'permissions': [],  # Item-үүдийн эрхээр шүүгдэнэ
        'items': [
            {
                'label': 'Бараа бүртгэл',
                'url_name': 'main:inventory_list',
                'icon': 'fas fa-boxes',
                'permissions': ['is_admin', 'is_accountant', 'perm:main.can_view_inventory', 'perm:main.view_product'],
            },
            {
                'label': 'Худалдан авалт',
                'url_name': 'main:purchase_create_multi',
                'icon': 'fas fa-arrow-down',
                'color': 'text-blue-600 hover:bg-blue-600',
                'permissions': ['is_admin', 'is_accountant', 'perm:main.can_manage_inventory', 'perm:main.add_purchase'],
            },
            {
                'label': 'Борлуулалт бүртгэх (Олон бараа)',
                'url_name': 'main:sale_create_multi',
                'icon': 'fas fa-shopping-basket',
                'color': 'text-green-600 hover:bg-green-600',
                'permissions': ['is_admin', 'is_accountant', 'perm:main.can_manage_inventory', 'perm:main.add_sale'],
            },
            {
                'label': 'Хөдөлгөөн',
                'url_name': 'main:stock_movement_list',
                'icon': 'fas fa-exchange-alt',
                'permissions': ['is_admin', 'is_accountant', 'perm:main.can_view_inventory', 'perm:main.view_stockmovement'],
            },
            {
                'label': 'Худалдан авалтын жагсаалт',
                'url_name': 'main:purchase_list',
                'icon': 'fas fa-shopping-cart',
                'permissions': ['is_admin', 'is_accountant', 'perm:main.can_view_inventory', 'perm:main.view_purchase'],
            },
            {
                'label': 'Борлуулалтын жагсаалт',
                'url_name': 'main:sale_list',
                'icon': 'fas fa-cash-register',
                'permissions': ['is_admin', 'is_accountant', 'perm:main.can_view_inventory', 'perm:main.view_sale'],
            },
        ]
    },
    {
        'section': '👥 Харилцагч',
        'icon': 'fas fa-users',
        'permissions': ['is_admin', 'is_accountant', 'perm:main.view_counterparty'],
        'items': [
            {
                'label': 'Харилцагчийн жагсаалт',
                'url_name': 'main:counterparty_list',
                'icon': 'fas fa-users',
                'permissions': ['is_admin', 'is_accountant', 'perm:main.view_counterparty'],
            },
            {
                'label': 'Харилцагч бүртгэх',
                'url_name': 'main:counterparty_create',
                'icon': 'fas fa-user-plus',
                'color': 'text-purple-600 hover:bg-purple-600',
                'permissions': ['is_admin', 'is_accountant', 'perm:main.add_counterparty'],
            },
        ]
    },
    {
        'section': '📊 Тайлан',
        'icon': 'fas fa-chart-bar',
        'permissions': [],  # Item-үүдээр шүүгдэнэ
        'items': [
            {
                'label': 'Товчоо тайлан /тоо ширхэг/',
                'url_name': 'main:inventory_summary_quantity',
                'icon': 'fas fa-chart-bar',
                'permissions': ['is_admin', 'is_accountant', 'perm:main.view_product'],
            },
            {
                'label': 'Товчоо тайлан /борлуулалт/',
                'url_name': 'main:inventory_summary_sales',
                'icon': 'fas fa-chart-line',
                'permissions': ['is_admin', 'is_accountant', 'perm:main.view_sale', 'perm:main.view_stockmovement'],
            },
            {
                'label': 'Товчоо тайлан /худалдан авалт/',
                'url_name': 'main:inventory_summary_purchases',
                'icon': 'fas fa-chart-area',
                'permissions': ['is_admin', 'is_accountant', 'perm:main.view_purchase', 'perm:main.view_stockmovement'],
            },
            {
                'label': 'Үлдэгдлийн тайлан',
                'url_name': 'main:inventory_balance_report',
                'icon': 'fas fa-balance-scale',
                'permissions': ['is_admin', 'is_accountant', 'perm:main.view_product'],
            },
            {
                'label': 'Банкны хуулгын тайлан',
                'url_name': 'main:bank_statement_report',
                'icon': 'fas fa-file-invoice-dollar',
                'permissions': ['is_admin', 'is_accountant', 'perm:main.view_banktransaction'],
            },
        ]
    },
    {
        'section': 'Сургалт',
        'icon': 'fas fa-graduation-cap',
        'permissions': ['is_admin', 'is_teacher', 'perm:main.view_course', 'perm:main.view_attendance'],  # Permission-басед шалгалт
        'items': [
            {
                'label': 'Хичээлүүд',
                'url_name': 'main:course_list',
                'icon': 'fas fa-graduation-cap',
                'permissions': ['is_admin', 'is_teacher', 'perm:main.view_course'],
            },
            {
                'label': 'Ирц бүртгэх',
                'url_name': 'main:attendance_list',
                'icon': 'fas fa-clipboard-check',
                'permissions': ['is_admin', 'is_teacher', 'perm:main.view_attendance'],  # Permission-басед
            },
            {
                'label': 'Бүртгэлүүд',
                'url_name': 'main:enrollment_list',
                'icon': 'fas fa-clipboard-list',
                'permissions': ['is_admin', 'is_manager', 'perm:main.view_enrollment'],  # Админ, Менежер
                'badge': 'pending_enrollments',  # Хүлээгдэж буй тоо харуулах
            },
            {
                'label': 'Төлбөр',
                'url_name': 'main:student_payments',
                'icon': 'fas fa-money-bill-wave',
                'permissions': ['is_admin', 'is_teacher', 'perm:main.view_enrollment'],  # Permission-басед
            },
            {
                'label': 'Сурагчид',
                'url_name': 'main:student_list',
                'icon': 'fas fa-users',
                'permissions': ['is_admin', 'perm:main.view_enrollment'],  # Permission-басед
            },
            {
                'label': 'Сурагч бүртгэх',
                'url_name': 'main:student_create',
                'icon': 'fas fa-user-plus',
                'permissions': ['is_admin', 'perm:main.add_enrollment'],  # Permission-басед
            },
            {
                'label': 'Багш нар',
                'url_name': 'main:teacher_list',
                'icon': 'fas fa-chalkboard-teacher',
                'permissions': ['is_admin'],
            },
            {
                'label': 'Багш бүртгэх',
                'url_name': 'main:teacher_create',
                'icon': 'fas fa-user-tie',
                'permissions': ['is_admin'],
            },
        ]
    },
    {
        'section': 'Удирдлага',
        'icon': 'fas fa-cog',
        'permissions': ['is_admin', 'is_superuser'],
        'items': [
            {
                'label': 'Хэрэглэгчийн эрх',
                'url_name': 'main:user_management',
                'icon': 'fas fa-users-cog',
                'permissions': ['is_admin', 'is_superuser'],
            },
            {
                'label': 'Эрхийн бүлгүүд (HTML)',
                'url_name': 'main:permission_group_list',
                'icon': 'fas fa-shield-alt',
                'permissions': ['is_admin', 'is_superuser'],
            },
            {
                'label': 'Эрхийн бүлгүүд (Хуучин)',
                'url_name': 'main:group_list',
                'icon': 'fas fa-users',
                'permissions': ['is_admin', 'is_superuser'],
            },
            {
                'label': 'Роль-ын мэдээлэл',
                'url_name': 'main:role_info',
                'icon': 'fas fa-id-badge',
                'permissions': ['authenticated'],  # Бүх нэвтэрсэн хэрэглэгч
            },
            {
                'label': 'Админ хэсэг',
                'url_name': 'admin:index',
                'icon': 'fas fa-cog',
                'permissions': ['is_staff'],
                'external': True,  # Админ панель бол шууд URL ашиглана
            },
        ]
    },
]


def user_has_permission(user, permissions):
    """
    Хэрэглэгч эрхтэй эсэхийг шалгах
    
    Боломжит эрхүүд:
    - 'authenticated': Нэвтэрсэн бүх хэрэглэгч
    - 'is_admin': Админ эрх
    - 'is_accountant': Нягтлан бодогч
    - 'is_teacher': Багш
    - 'is_staff': Staff статустай
    - 'is_superuser': Superuser
    - 'role:MANAGER': Тодорхой роль (Харин бүлгээр удирдахыг зөвлөнө!)
    - 'group:Менежер': Тодорхой бүлэг (HTML дээрээс удирдана)
    - 'perm:main.add_product': Django permission
    """
    if not user.is_authenticated:
        return False
    
    # Нэг ч эрх заaагүй бол бүх нэвтэрсэн хэрэглэгчид харагдана
    if not permissions:
        return True
    
    for permission in permissions:
        # Authenticated
        if permission == 'authenticated' and user.is_authenticated:
            return True
        
        # Profile-based эрхүүд
        if hasattr(user, 'profile'):
            profile = user.profile
            
            # Superuser бол зөвхөн admin эрх шаардсан цэсүүдийг харна
            if permission == 'is_admin' and (profile.is_admin or user.is_superuser):
                return True
            if permission == 'is_manager' and profile.role == 'MANAGER':  # Зөвхөн MANAGER роль, админ биш!
                return True
            if permission == 'is_accountant' and (profile.is_accountant or user.is_superuser):
                return True
            if permission == 'is_teacher' and profile.is_teacher:
                return True
            
            # Role шалгах
            if permission.startswith('role:'):
                role_name = permission.split(':')[1]
                if profile.role == role_name:
                    return True
        
        # User-based эрхүүд
        if permission == 'is_staff' and user.is_staff:
            return True
        if permission == 'is_superuser' and user.is_superuser:
            return True
        
        # Group шалгах
        if permission.startswith('group:'):
            group_name = permission.split(':')[1]
            if user.groups.filter(name=group_name).exists():
                return True
        
        # Django permission шалгах
        if permission.startswith('perm:'):
            perm_name = permission.split(':')[1]
            if user.has_perm(perm_name):
                return True
    
    return False


def get_user_menu(user):
    """Хэрэглэгчийн эрхээр нь SIDEBAR цэс буцаах"""
    filtered_menu = []
    
    for section in SIDEBAR_MENU:
        # Section эрх шалгах
        if not user_has_permission(user, section.get('permissions', [])):
            continue
        
        # Items шүүх
        filtered_items = []
        for item in section.get('items', []):
            if user_has_permission(user, item.get('permissions', [])):
                filtered_items.append(item)
        
        # Хоосон section харуулахгүй
        if filtered_items:
            section_copy = section.copy()
            section_copy['items'] = filtered_items
            filtered_menu.append(section_copy)
    
    return filtered_menu


def get_header_menu(user):
    """Header navigation цэс буцаах (public + private items)"""
    filtered_menu = []
    
    for item in HEADER_MENU:
        # Эрх шалгах
        if not user_has_permission(user, item.get('permissions', [])):
            continue
        
        # Dropdown бол items-ийг шүүх
        if item.get('is_dropdown') and 'items' in item:
            filtered_items = []
            for sub_item in item['items']:
                if user_has_permission(user, sub_item.get('permissions', [])):
                    filtered_items.append(sub_item)
            
            # Dropdown хоосон бол харуулахгүй
            if filtered_items:
                item_copy = item.copy()
                item_copy['items'] = filtered_items
                filtered_menu.append(item_copy)
        else:
            # Энгийн линк
            filtered_menu.append(item)
    
    return filtered_menu
