from django.core.management.base import BaseCommand
from main.models import PageContent


class Command(BaseCommand):
    help = 'Бүх хуудасны анхдагч агуулга үүсгэх'

    def handle(self, *args, **kwargs):
        all_contents = [
            # Нүүр хуудас агуулгууд (аль хэдийн байгаа)
            # ... home агуулгууд init_page_content.py дээр байна
            
            # Бидний тухай хуудас
            {'key': 'about_title', 'title': 'Бидний тухай - Гарчиг', 'content': 'Бидний тухай', 'page': 'about'},
            {'key': 'about_subtitle', 'title': 'Бидний тухай - Дэд гарчиг', 'content': 'Готопа бясалгалын төв', 'page': 'about'},
            {'key': 'about_description', 'title': 'Бидний тухай - Тайлбар', 'content': 'Бид 2010 оноос эхлэн Готопа бясалгалыг Монголд түгээн дэлгэрүүлж ирсэн.', 'page': 'about'},
            
            # Готопа бясалгал хуудас
            {'key': 'gotopa_title', 'title': 'Готопа бясалгал - Гарчиг', 'content': 'Готопа бясалгал гэж юу вэ?', 'page': 'home'},
            {'key': 'gotopa_intro', 'title': 'Готопа бясалгал - Танилцуулга', 'content': 'Өндөр давтамжийн бясалгал', 'page': 'home'},
            
            # Гүрү Готопа багш
            {'key': 'guru_title', 'title': 'Гүрү - Гарчиг', 'content': 'Гүрү Готопа багш', 'page': 'home'},
            {'key': 'guru_description', 'title': 'Гүрү - Тайлбар', 'content': 'Олон улсад алдартай багш', 'page': 'home'},
            
            # Бясалгалын төв
            {'key': 'center_title', 'title': 'Төв - Гарчиг', 'content': 'Бясалгалын төв', 'page': 'home'},
            {'key': 'center_address', 'title': 'Төв - Хаяг', 'content': 'Улаанбаатар хот', 'page': 'contact'},
            
            # Мэдээлэл
            {'key': 'news_title', 'title': 'Мэдээ - Гарчиг', 'content': 'Мэдээ мэдээлэл', 'page': 'home'},
            {'key': 'news_latest', 'title': 'Мэдээ - Сүүлийн үеийн', 'content': 'Сүүлийн үеийн мэдээ', 'page': 'home'},
            
            # Хичээлүүд
            {'key': 'courses_title', 'title': 'Хичээл - Гарчиг', 'content': 'Бясалгалын сургалтууд', 'page': 'courses'},
            {'key': 'beginner_title', 'title': 'Анхан шат - Гарчиг', 'content': 'Анхан шатны бясалгал', 'page': 'courses'},
            {'key': 'beginner_description', 'title': 'Анхан шат - Тайлбар', 'content': '3 сарын сургалт', 'page': 'courses'},
            {'key': 'intermediate_title', 'title': 'Дунд шат - Гарчиг', 'content': 'Дунд шатны бясалгал', 'page': 'courses'},
            {'key': 'advanced_title', 'title': 'Дээд шат - Гарчиг', 'content': 'Дээд шатны бясалгал', 'page': 'courses'},
            {'key': 'vip_title', 'title': 'VIP - Гарчиг', 'content': 'Зуны VIP бясалгал', 'page': 'courses'},
            
            # Бүтээгдэхүүн
            {'key': 'products_title', 'title': 'Бүтээгдэхүүн - Гарчиг', 'content': 'Бүтээгдэхүүн үйлчилгээ', 'page': 'other'},
            {'key': 'books_title', 'title': 'Ном - Гарчиг', 'content': 'Хэвлэгдэн гарсан номууд', 'page': 'other'},
            
            # Аялал
            {'key': 'travel_title', 'title': 'Аялал - Гарчиг', 'content': 'Номхон далайн аялал', 'page': 'other'},
            {'key': 'travel_description', 'title': 'Аялал - Тайлбар', 'content': 'Жил бүрийн аялал', 'page': 'other'},
            
            # Холбоо барих
            {'key': 'contact_title', 'title': 'Холбоо - Гарчиг', 'content': 'Холбоо барих', 'page': 'contact'},
            {'key': 'contact_phone', 'title': 'Холбоо - Утас', 'content': '+976 99001234', 'page': 'contact'},
            {'key': 'contact_email', 'title': 'Холбоо - Имэйл', 'content': 'info@gotopa.mn', 'page': 'contact'},
        ]

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for data in all_contents:
            try:
                content, created = PageContent.objects.update_or_create(
                    key=data['key'],
                    defaults={
                        'title': data['title'],
                        'content': data['content'],
                        'page': data['page'],
                        'is_active': True
                    }
                )
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Үүсгэсэн: {content.title}')
                    )
                else:
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'○ Шинэчилсэн: {content.title}')
                    )
            except Exception as e:
                skipped_count += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ Алдаа ({data["key"]}): {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Дууслаа! Үүсгэсэн: {created_count}, Шинэчилсэн: {updated_count}, Алдаа: {skipped_count}'
            )
        )
