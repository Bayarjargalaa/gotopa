from django.core.management.base import BaseCommand
from main.models import CashFlowIndicator


class Command(BaseCommand):
    help = 'Мөнгөн гүйлгээний үзүүлэлтүүдийг үүсгэх'

    def handle(self, *args, **options):
        # Бүх өмнөх өгөгдлийг устгах
        CashFlowIndicator.objects.all().delete()
        
        indicators_data = [
            # 1. Үндсэн үйл ажиллагааны мөнгөн гүйлгээ
            {'code': '1', 'name': 'Үндсэн үйл ажиллагааны мөнгөн гүйлгээ', 'flow_type': 'BOTH', 'level': 1},
            {'code': '1.1', 'name': 'Мөнгөн орлогын дүн', 'flow_type': 'INCOME', 'level': 2, 'parent_code': '1'},
            {'code': '1.1.1', 'name': 'Бараа борлуулсан, үйлчилгээ үзүүлсний орлого', 'flow_type': 'INCOME', 'level': 3, 'parent_code': '1.1'},
            {'code': '1.1.2', 'name': 'Эрхийн шимтгэл, хураамж, төлбөрийн орлого', 'flow_type': 'INCOME', 'level': 3, 'parent_code': '1.1'},
            {'code': '1.1.3', 'name': 'Даатгалын нөхвөрөөс хүлээн авсан мөнгө', 'flow_type': 'INCOME', 'level': 3, 'parent_code': '1.1'},
            {'code': '1.1.4', 'name': 'Буцаан авсан албан татвар', 'flow_type': 'INCOME', 'level': 3, 'parent_code': '1.1'},
            {'code': '1.1.5', 'name': 'Татаас, санхүүжилтийн орлого', 'flow_type': 'INCOME', 'level': 3, 'parent_code': '1.1'},
            {'code': '1.1.6', 'name': 'Бусад мөнгөн орлого', 'flow_type': 'INCOME', 'level': 3, 'parent_code': '1.1'},
            
            {'code': '1.2', 'name': 'Мөнгөн зарлагын дүн (-)', 'flow_type': 'EXPENSE', 'level': 2, 'parent_code': '1'},
            {'code': '1.2.1', 'name': 'Ажиллагчдад төлсөн', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '1.2'},
            {'code': '1.2.2', 'name': 'Нийгмийн даатгалын байгууллагад төлсөн', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '1.2'},
            {'code': '1.2.3', 'name': 'Бараа материал худалдан авахад төлсөн', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '1.2'},
            {'code': '1.2.4', 'name': 'Ашиглалтын зардал төлсөн', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '1.2'},
            {'code': '1.2.5', 'name': 'Түлш шатахуун, тээврийн хөлс, сэлбэг хэрэгсэлд төлсөн', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '1.2'},
            {'code': '1.2.6', 'name': 'Хүүний төлбөрт төлсөн', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '1.2'},
            {'code': '1.2.7', 'name': 'Татварын байгууллагад төлсөн', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '1.2'},
            {'code': '1.2.8', 'name': 'Даатгалын төлбөрт төлсөн', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '1.2'},
            {'code': '1.2.9', 'name': 'Бусад мөнгөн зарлага', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '1.2'},
            
            {'code': '1.3', 'name': 'Үндсэн үйл ажиллагааны цэвэр мөнгөн гүйлгээний дүн', 'flow_type': 'BOTH', 'level': 2, 'parent_code': '1'},
            
            # 2. Хөрөнгө оруулалтын үйл ажиллагааны мөнгөн гүйлгээ
            {'code': '2', 'name': 'Хөрөнгө оруулалтын үйл ажиллагааны мөнгөн гүйлгээ', 'flow_type': 'BOTH', 'level': 1},
            {'code': '2.1', 'name': 'Мөнгөн орлогын дүн', 'flow_type': 'INCOME', 'level': 2, 'parent_code': '2'},
            {'code': '2.1.1', 'name': 'Үндсэн хөрөнгө борлуулсны орлого', 'flow_type': 'INCOME', 'level': 3, 'parent_code': '2.1'},
            {'code': '2.1.2', 'name': 'Биет бус хөрөнгө борлуулсны орлого', 'flow_type': 'INCOME', 'level': 3, 'parent_code': '2.1'},
            {'code': '2.1.3', 'name': 'Хөрөнгө оруулалт борлуулсны орлого', 'flow_type': 'INCOME', 'level': 3, 'parent_code': '2.1'},
            {'code': '2.1.4', 'name': 'Бусад урт хугацаат хөрөнгө борлуулсны орлого', 'flow_type': 'INCOME', 'level': 3, 'parent_code': '2.1'},
            {'code': '2.1.5', 'name': 'Бусдад олгосон зээл, мөнгөн   урьдчилгааны буцаан төлөлт', 'flow_type': 'INCOME', 'level': 3, 'parent_code': '2.1'},
            {'code': '2.1.6', 'name': 'Хүлээн авсан хүүний орлого', 'flow_type': 'INCOME', 'level': 3, 'parent_code': '2.1'},
            {'code': '2.1.7', 'name': 'Хүлээн авсан ногдол ашиг', 'flow_type': 'INCOME', 'level': 3, 'parent_code': '2.1'},
            
            {'code': '2.2', 'name': 'Мөнгөн зарлагын дүн', 'flow_type': 'EXPENSE', 'level': 2, 'parent_code': '2'},
            {'code': '2.2.1', 'name': 'Үндсэн хөрөнгө олж эзэмшихэд төлсөн', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '2.2'},
            {'code': '2.2.2', 'name': 'Биет бус хөрөнгө олж эзэмшихэд төлсөн', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '2.2'},
            {'code': '2.2.3', 'name': 'Хөрөнгө оруулалт олж эзэмшихэд төлсөн', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '2.2'},
            {'code': '2.2.4', 'name': 'Бусад урт хугацаат хөрөнгө олж эзэмшихэд төлсөн', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '2.2'},
            {'code': '2.2.5', 'name': 'Бусад олгосон зээл болон урьдчилгаа', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '2.2'},
            
            {'code': '2.3', 'name': 'Хөрөнгө оруулалтын үйл ажиллагааны цэвэр мөнгөн гүйлгээний дүн', 'flow_type': 'BOTH', 'level': 2, 'parent_code': '2'},
            
            # 3. Санхүү үйл ажиллагааны мөнгөн гүйлгээ
            {'code': '3', 'name': 'Санхүү үйл ажиллагааны мөнгөн гүйлгээ', 'flow_type': 'BOTH', 'level': 1},
            {'code': '3.1', 'name': 'Мөнгөн орлогын дүн', 'flow_type': 'INCOME', 'level': 2, 'parent_code': '3'},
            {'code': '3.1.1', 'name': 'Зээл авсан, өрийн үнэт цаас гаргаснаас хүлээн авсан', 'flow_type': 'INCOME', 'level': 3, 'parent_code': '3.1'},
            {'code': '3.1.2', 'name': 'Хувьцаа болон өмчийн бусад үнэт цаас гаргаснаас хүлээн авсан', 'flow_type': 'INCOME', 'level': 3, 'parent_code': '3.1'},
            {'code': '3.1.3', 'name': 'Төрөл бүрийн хандив', 'flow_type': 'INCOME', 'level': 3, 'parent_code': '3.1'},
            
            {'code': '3.2', 'name': 'Мөнгөн зарлагын дүн', 'flow_type': 'EXPENSE', 'level': 2, 'parent_code': '3'},
            {'code': '3.2.1', 'name': 'Зээл, өрийн үнэт цаасны төлбөрт төлсөн мөнгө', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '3.2'},
            {'code': '3.2.2', 'name': 'Санхүүгийн түрээсийн өглөгт төлсөн', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '3.2'},
            {'code': '3.2.3', 'name': 'Хувьцаа буцаан худалдаж авахад төлсөн', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '3.2'},
            {'code': '3.2.4', 'name': 'Төлсөн ногдол ашиг', 'flow_type': 'EXPENSE', 'level': 3, 'parent_code': '3.2'},
            
            {'code': '3.3', 'name': 'Санхүүгийн үйл ажиллагааны цэвэр мөнгөн гүйлгээний дүн', 'flow_type': 'BOTH', 'level': 2, 'parent_code': '3'},
            
            # 4-6
            {'code': '4', 'name': 'Валютын ханшийн зөрүү', 'flow_type': 'BOTH', 'level': 1},
            {'code': '4.1', 'name': 'Бүх цэвэр мөнгөн гүйлгээ', 'flow_type': 'BOTH', 'level': 2, 'parent_code': '4'},
            {'code': '5', 'name': 'Мөнгө, түүнтэй адилтгах хөрөнгийн эхний үлдэгдэл', 'flow_type': 'BOTH', 'level': 1},
            {'code': '6', 'name': 'Мөнгө, түүнтэй адилтгах хөрөнгийн эцсийн үлдэгдэл', 'flow_type': 'BOTH', 'level': 1},
        ]
        
        # Эцэг үзүүлэлтүүдийг эхлээд үүсгэх
        parent_map = {}
        
        for data in indicators_data:
            parent_code = data.pop('parent_code', None)
            indicator = CashFlowIndicator.objects.create(**data)
            parent_map[data['code']] = indicator
            
            if parent_code and parent_code in parent_map:
                indicator.parent = parent_map[parent_code]
                indicator.save()
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ {len(indicators_data)} ширхэг мөнгөн гүйлгээний үзүүлэлт үүсгэгдлээ')
        )
