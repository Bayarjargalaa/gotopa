"""
Харилцагчдын мэдээллийг Excel файлаас импортлох

Ашиглах заавар:
python manage.py shell
>>> from main.import_counterparties import import_counterparties
>>> import_counterparties('харилцагчид.xlsx')

Excel файлын формат:
- Нэр | Төрөл | Утас | Имэйл | Хаяг | Регистр | Татвар | Харилцах үлдэгдэл | Тэмдэглэл
"""

import pandas as pd
from main.models import Counterparty
from decimal import Decimal


def import_counterparties(excel_file):
    """
    Excel файлаас харилцагчдын мэдээллийг импортлох
    
    Parameters:
    excel_file (str): Excel файлын нэр эсвэл path
    """
    try:
        df = pd.read_excel(excel_file, engine='openpyxl')
        
        print(f"Нийт мөр: {len(df)}")
        print(f"Баганууд: {list(df.columns)}")
        
        created_count = 0
        updated_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                name = str(row.get('Нэр', '')).strip() if pd.notna(row.get('Нэр')) else ''
                
                if not name:
                    print(f"Мөр {index + 2}: Нэр хоосон байна, алгасав.")
                    error_count += 1
                    continue
                
                # Төрөл тодорхойлох
                counterparty_type_str = str(row.get('Төрөл', 'Хоёулаа')).strip().upper() if pd.notna(row.get('Төрөл')) else 'BOTH'
                
                if 'НИЙЛҮҮЛ' in counterparty_type_str or 'SUPPLIER' in counterparty_type_str:
                    counterparty_type = 'SUPPLIER'
                elif 'ҮЙЛЧЛҮҮЛ' in counterparty_type_str or 'CUSTOMER' in counterparty_type_str:
                    counterparty_type = 'CUSTOMER'
                else:
                    counterparty_type = 'BOTH'
                
                phone = str(row.get('Утас', '')).strip() if pd.notna(row.get('Утас')) else ''
                email = str(row.get('Имэйл', '')).strip() if pd.notna(row.get('Имэйл')) else ''
                address = str(row.get('Хаяг', '')).strip() if pd.notna(row.get('Хаяг')) else ''
                contact_person = str(row.get('Холбоо барих', '')).strip() if pd.notna(row.get('Холбоо барих')) else ''
                registration_number = str(row.get('Регистр', '')).strip() if pd.notna(row.get('Регистр')) else ''
                tax_number = str(row.get('Татвар', '')).strip() if pd.notna(row.get('Татвар')) else ''
                notes = str(row.get('Тэмдэглэл', '')).strip() if pd.notna(row.get('Тэмдэглэл')) else ''
                
                # Харилцах үлдэгдэл
                balance = 0
                if pd.notna(row.get('Харилцах үлдэгдэл')):
                    try:
                        balance = Decimal(str(row.get('Харилцах үлдэгдэл', 0)))
                    except:
                        balance = 0
                
                # Counterparty үүсгэх эсвэл шинэчлэх
                counterparty, created = Counterparty.objects.update_or_create(
                    name=name,
                    defaults={
                        'counterparty_type': counterparty_type,
                        'phone': phone,
                        'email': email if email and '@' in email else '',
                        'address': address,
                        'contact_person': contact_person,
                        'registration_number': registration_number,
                        'tax_number': tax_number,
                        'balance': balance,
                        'notes': notes,
                    }
                )
                
                if created:
                    created_count += 1
                    print(f"✓ Үүсгэв: {name} ({counterparty.get_counterparty_type_display()})")
                else:
                    updated_count += 1
                    print(f"↻ Шинэчиллээ: {name}")
                
            except Exception as e:
                error_count += 1
                print(f"✗ Мөр {index + 2} алдаа: {str(e)}")
                continue
        
        print("\n" + "="*50)
        print(f"Дүн:")
        print(f"  Шинээр үүссэн: {created_count}")
        print(f"  Шинэчилсэн: {updated_count}")
        print(f"  Алдаа: {error_count}")
        print(f"  Нийт: {created_count + updated_count}")
        print("="*50)
        
        return {
            'created': created_count,
            'updated': updated_count,
            'errors': error_count
        }
        
    except FileNotFoundError:
        print(f"✗ Файл олдсонгүй: {excel_file}")
        return None
    except Exception as e:
        print(f"✗ Алдаа гарлаа: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    print("Энэ script-ийг Django shell-ээс ажиллуулна уу:")
    print("python manage.py shell")
    print(">>> from main.import_counterparties import import_counterparties")
    print(">>> import_counterparties('харилцагчид.xlsx')")
