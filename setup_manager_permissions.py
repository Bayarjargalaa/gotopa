"""
"Менежер" бүлэгт бүх шаардлагатай эрхүүд өгөх
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from django.contrib.auth.models import Group, Permission

# Менежер бүлэг авах/үүсгэх
group, created = Group.objects.get_or_create(name='Менежер')
if created:
    print("✓ 'Менежер' бүлэг үүсгэгдлээ")
else:
    print("✓ 'Менежер' бүлэг байгаа")

# Inventory эрхүүд
inventory_perms = [
    # Custom permissions
    'can_view_inventory',
    'can_manage_inventory',
    
    # Product permissions
    'view_product',
    'add_product',
    'change_product',
    'delete_product',
    
    # Purchase permissions
    'view_purchase',
    'add_purchase',
    'change_purchase',
    'delete_purchase',
    
    # Sale permissions
    'view_sale',
    'add_sale',
    'change_sale',
    'delete_sale',
    
    # Stock movement
    'view_stockmovement',
    'add_stockmovement',
    'change_stockmovement',
    'delete_stockmovement',
    
    # Counterparty (Харилцагч)
    'view_counterparty',
    'add_counterparty',
    'change_counterparty',
    'delete_counterparty',
]

# Training/Course permissions
training_perms = [
    'view_course',
    'add_course',
    'change_course',
    'delete_course',
    'view_enrollment',
    'add_enrollment',
    'change_enrollment',
    'delete_enrollment',
    'view_attendance',
    'add_attendance',
    'change_attendance',
    'delete_attendance',
]

all_perms = inventory_perms + training_perms

print(f"\n📋 {len(all_perms)} эрх нэмэх гэж байна...")
print("=" * 80)

added = 0
already_exists = 0
not_found = 0

for codename in all_perms:
    try:
        perm = Permission.objects.get(codename=codename, content_type__app_label='main')
        if group.permissions.filter(id=perm.id).exists():
            print(f"  ⏭️  {perm.name} (аль хэдийн байгаа)")
            already_exists += 1
        else:
            group.permissions.add(perm)
            print(f"  ✓ {perm.name}")
            added += 1
    except Permission.DoesNotExist:
        print(f"  ✗ {codename} олдсонгүй")
        not_found += 1

print("=" * 80)
print(f"📊 ДҮГНЭЛТ:")
print(f"  ✓ Нэмэгдсэн: {added}")
print(f"  ⏭️  Аль хэдийн байсан: {already_exists}")
print(f"  ✗ Олдоогүй: {not_found}")
print(f"  📦 Нийт: {group.permissions.count()} эрх")
print("=" * 80)
