from django.core.management.base import BaseCommand
from main.models import PageContent

class Command(BaseCommand):
    help = 'Create comprehensive About page content'

    def handle(self, *args, **options):
        contents = [
            # About page - Main sections
            {'key': 'about_mission_title', 'title': 'Mission Title', 'content': 'Бидний эрхэм зорилго', 'page': 'about'},
            {'key': 'about_mission_desc', 'title': 'Mission Description', 'content': 'Готопа бясалгалын өндөр давтамжийн аргыг Монголд түгээн дэлгэрүүлж, хүмүүст гэгээрэл, эрүүл мэнд, оюун санааны амар амгаланд хүрэх замыг зааж өгөх', 'page': 'about'},
            
            {'key': 'about_vision_title', 'title': 'Vision Title', 'content': 'Бидний алсын хараа', 'page': 'about'},
            {'key': 'about_vision_desc', 'title': 'Vision Description', 'content': 'Монгол улсад бясалгалын соёлыг төлөвшүүлж, хүн бүр өөрийн мөн чанарыг таньж, гэгээрэлд хүрэх боломжтой нийгэм бүтээх', 'page': 'about'},
            
            # History
            {'key': 'about_history_title', 'title': 'History Title', 'content': 'Түүхэн замнал', 'page': 'about'},
            {'key': 'about_history_2010', 'title': 'History 2010', 'content': '2010 онд Гүрү Готопа багш Монголд анхны сургалтаа зохион байгууллаа.', 'page': 'about'},
            {'key': 'about_history_2015', 'title': 'History 2015', 'content': '2015 онд Улаанбаатар хотод Готопа бясалгалын төв албан ёсоор нээгдсэн.', 'page': 'about'},
            {'key': 'about_history_2020', 'title': 'History 2020', 'content': '2020 онд 1000 гаруй оюутан бясалгалын сургалтад хамрагдсан.', 'page': 'about'},
            
            # Values
            {'key': 'about_values_title', 'title': 'Values Title', 'content': 'Бидний үнэт зүйлс', 'page': 'about'},
            {'key': 'about_value1_title', 'title': 'Value 1 Title', 'content': 'Гэгээн гэрэл', 'page': 'about'},
            {'key': 'about_value1_desc', 'title': 'Value 1 Description', 'content': 'Бид хүн бүрийн дотор байгаа гэрлийг асааж, гэгээрэлд хүргэхэд чиглэнэ.', 'page': 'about'},
            {'key': 'about_value2_title', 'title': 'Value 2 Title', 'content': 'Хайр энэрэл', 'page': 'about'},
            {'key': 'about_value2_desc', 'title': 'Value 2 Description', 'content': 'Хайр энэрлээр дамжуулан бусадтай хуваалцах нь бидний үндсэн зарчим.', 'page': 'about'},
            {'key': 'about_value3_title', 'title': 'Value 3 Title', 'content': 'Үнэн шударга байдал', 'page': 'about'},
            {'key': 'about_value3_desc', 'title': 'Value 3 Description', 'content': 'Бид үнэн шударга байдал, ил тод байдлыг эрхэмлэдэг.', 'page': 'about'},
            
            # Team
            {'key': 'about_team_title', 'title': 'Team Title', 'content': 'Бидний баг', 'page': 'about'},
            {'key': 'about_team_intro', 'title': 'Team Introduction', 'content': 'Манай баг туршлагатай багш нар, сайн дурын ажилтнуудаас бүрдэнэ.', 'page': 'about'},
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
