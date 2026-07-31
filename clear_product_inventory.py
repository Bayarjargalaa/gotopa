"""
Сонгосон бүтээгдэхүүний хөдөлгөөн болон үлдэгдлийг цэвэрлэх скрипт
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import StockMovement, Product
from django.db import transaction

def clear_product_inventory():
    """Сонгосон бүтээгдэхүүний өгөгдлийг цэвэрлэх"""
    
    print("=" * 60)
    print("БҮТЭЭГДЭХҮҮНИЙ ӨГӨГДӨЛ ЦЭВЭРЛЭХ")
    print("=" * 60)
    
    # Бүх бүтээгдэхүүнийг харуулах
    products = Product.objects.all().order_by('name')
    
    if not products.exists():
        print("\n❌ Ямар ч бүтээгдэхүүн олдсонгүй!")
        return
    
    print("\nБүтээгдэхүүний жагсаалт:")
    print("-" * 60)
    for i, product in enumerate(products, 1):
        movements_count = product.movements.count()
        print(f"{i}. {product.name}")
        print(f"   Үлдэгдэл: {product.current_stock}, Хөдөлгөөн: {movements_count}")
    
    print("-" * 60)
    print(f"0. БҮХ бүтээгдэхүүнийг цэвэрлэх")
    print("q. Буцах")
    
    choice = input("\n🔹 Сонголт (дугаар оруулна уу): ")
    
    if choice.lower() == 'q':
        print("\n❌ Үйлдэл цуцлагдлаа.")
        return
    
    try:
        choice_num = int(choice)
        
        if choice_num == 0:
            # Бүх бүтээгдэхүүн
            selected_products = list(products)
            print(f"\n⚠️  БҮХ {len(selected_products)} бүтээгдэхүүний өгөгдлийг устгах гэж байна!")
        elif 1 <= choice_num <= len(products):
            # Нэг бүтээгдэхүүн
            selected_products = [products[choice_num - 1]]
            print(f"\n🔹 Сонгосон: {selected_products[0].name}")
        else:
            print("\n❌ Буруу сонголт!")
            return
        
        confirm = input("\n🔴 Үргэлжлүүлэх уу? (yes гэж бичнэ үү): ")
        
        if confirm.lower() != 'yes':
            print("\n❌ Үйлдэл цуцлагдлаа.")
            return
        
        with transaction.atomic():
            total_movements = 0
            
            for product in selected_products:
                # Хөдөлгөөн устгах
                movements = product.movements.all()
                count = movements.count()
                movements.delete()
                total_movements += count
                
                # Үлдэгдэл 0 болгох
                product.current_stock = 0
                product.save()
                
                print(f"✅ {product.name}: {count} хөдөлгөөн устгагдлаа")
            
            print(f"\n🎉 Нийт {total_movements} хөдөлгөөн амжилттай устгагдлаа!")
            
    except ValueError:
        print("\n❌ Зөв дугаар оруулна уу!")
    except Exception as e:
        print(f"\n❌ Алдаа гарлаа: {str(e)}")

if __name__ == '__main__':
    clear_product_inventory()
