from django.core.management.base import BaseCommand
from main.models import PageContent

class Command(BaseCommand):
    help = 'Create missing PageContent entries for home page'

    def handle(self, *args, **options):
        contents = [
            # Features
            {'key': 'home_feature1_title', 'title': 'Feature 1 Title', 'content': 'Бясалгал гэж юу вэ?', 'page': 'home'},
            {'key': 'home_feature1_desc', 'title': 'Feature 1 Description', 'content': 'Бид хэрхэн бясалгал хийдэг вэ?', 'page': 'home'},
            {'key': 'home_feature2_title', 'title': 'Feature 2 Title', 'content': 'Ном', 'page': 'home'},
            {'key': 'home_feature2_desc', 'title': 'Feature 2 Description', 'content': 'Хэвлэгдэн гарсан номууд', 'page': 'home'},
            {'key': 'home_feature3_title', 'title': 'Feature 3 Title', 'content': 'Тайлбар үгс', 'page': 'home'},
            {'key': 'home_feature3_desc', 'title': 'Feature 3 Description', 'content': 'Сайтад орсон үгсийн тайлбаруud', 'page': 'home'},
            
            # About Section
            {'key': 'home_about_subtitle', 'title': 'About Subtitle', 'content': 'Бясалгалыг сонгох давуу талууд', 'page': 'home'},
            {'key': 'home_about_benefit1', 'title': 'About Benefit 1', 'content': 'Гүрү Готопа багш заана', 'page': 'home'},
            {'key': 'home_about_benefit2', 'title': 'About Benefit 2', 'content': 'Анхан шатны 3 сарын сургалт: Долоо хоног бүр 2 удаа, 5 цаг орно.', 'page': 'home'},
            {'key': 'home_about_benefit3', 'title': 'About Benefit 3', 'content': 'Хичээллэх тав тухтай орчин', 'page': 'home'},
            {'key': 'home_about_benefit4', 'title': 'About Benefit 4', 'content': 'Баталгаажсан үр дүн', 'page': 'home'},
        ]
        
        created = 0
        updated = 0
        
        for content_data in contents:
            obj, created_now = PageContent.objects.update_or_create(
                key=content_data['key'],
                defaults={
                    'title': content_data['title'],
                    'content': content_data['content'],
                    'page': content_data['page'],
                    'is_active': True
                }
            )
            if created_now:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Үүсгэсэн: {content_data["key"]}'))
            else:
                updated += 1
                self.stdout.write(f'  Шинэчилсэн: {content_data["key"]}')
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Дууслаа! Үүсгэсэн: {created}, Шинэчилсэн: {updated}'))
