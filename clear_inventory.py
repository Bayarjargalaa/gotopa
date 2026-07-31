"""
Бүх бараа материалын хөдөлгөөн болон үлдэгдлийг цэвэрлэх скрипт
АНХААРУУЛГА: Энэ нь БҮХ өгөгдлийг устгана!
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import StockMovement, Product
from django.db import transaction

def clear_inventory():
    """Бүх бараа материалын өгөгдлийг цэвэрлэх"""
    
    print("=" * 60)
    print("БАРАА МАТЕРИАЛЫН ӨГӨГДӨЛ ЦЭВЭРЛЭХ")
    print("=" * 60)
    
    # Одоогийн байдал
    movement_count = StockMovement.objects.count()
    product_count = Product.objects.count()
    
    print(f"\nОдоогийн байдал:")
    print(f"  - Бараа материалын хөдөлгөөн: {movement_count}")
    print(f"  - Бүтээгдэхүүний тоо: {product_count}")
    
    if movement_count == 0 and all(p.current_stock == 0 for p in Product.objects.all()):
        print("\n✅ Өгөгдөл аль хэдийн цэвэр байна!")
        return
    
    # Баталгаажуулалт
    print("\n⚠️  АНХААРУУЛГА: Энэ үйлдэл БҮХ дараах өгөгдлийг устгана:")
    print("  1. Бүх бараа материалын хөдөлгөөн (худалдан авалт, борлуулалт)")
    print("  2. Холбогдох журналын бичилтүүд")
    print("  3. Бүх бүтээгдэхүүний үлдэгдлийг 0 болгоно")
    
    confirm = input("\n🔴 Үргэлжлүүлэх уу? (yes гэж бичнэ үү): ")
    
    if confirm.lower() != 'yes':
        print("\n❌ Үйлдэл цуцлагдлаа.")
        return
    
    try:
        with transaction.atomic():
            # 1. Бараа материалын хөдөлгөөн устгах (журналын бичилт автоматаар устана CASCADE-р)
            deleted_movements = StockMovement.objects.all().delete()
            print(f"\n✅ {deleted_movements[0]} хөдөлгөөн устгагдлаа")
            
            # 2. Бүх бүтээгдэхүүний үлдэгдлийг 0 болгох
            products = Product.objects.all()
            for product in products:
                product.current_stock = 0
                product.save()
            
            print(f"✅ {product_count} бүтээгдэхүүний үлдэгдэл 0 болгогдлоо")
            
            print("\n" + "=" * 60)
            print("🎉 БҮХ ӨГӨГДӨЛ АМЖИЛТТАЙ ЦЭВЭРЛЭГДЛЭЭ!")
            print("=" * 60)
            
            # Эцсийн байдал
            print(f"\nЭцсийн байдал:")
            print(f"  - Бараа материалын хөдөлгөөн: {StockMovement.objects.count()}")
            print(f"  - Үлдэгдэлтэй бүтээгдэхүүн: {Product.objects.filter(current_stock__gt=0).count()}")
            
    except Exception as e:
        print(f"\n❌ Алдаа гарлаа: {str(e)}")
        print("   Бүх өөрчлөлт буцаагдлаа (transaction rollback)")

if __name__ == '__main__':
    clear_inventory()
