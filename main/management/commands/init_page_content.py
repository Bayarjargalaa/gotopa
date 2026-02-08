from django.core.management.base import BaseCommand
from main.models import PageContent


class Command(BaseCommand):
    help = 'Нүүр хуудасны анхдагч агуулга үүсгэх'

    def handle(self, *args, **kwargs):
        # Нүүр хуудасны агуулгууд
        home_contents = [
            {
                'key': 'home_hero_subtitle',
                'title': 'Нүүр - Hero дэд гарчиг',
                'content': 'Готопа бясалгал бол',
                'page': 'home'
            },
            {
                'key': 'home_hero_title',
                'title': 'Нүүр - Hero үндсэн гарчиг',
                'content': 'Хүн төрөлхтөнд барих бэлэг',
                'page': 'home'
            },
            {
                'key': 'home_hero_description',
                'title': 'Нүүр - Hero тайлбар',
                'content': 'Өндөр давтамжийн бясалгал',
                'page': 'home'
            },
            {
                'key': 'home_hero_btn_learn',
                'title': 'Нүүр - Hero товч (Дэлгэрэнгүй)',
                'content': 'Дэлгэрэнгүй',
                'page': 'home'
            },
            {
                'key': 'home_hero_btn_register',
                'title': 'Нүүр - Hero товч (Бүртгүүлэх)',
                'content': 'Бүртгүүлэх',
                'page': 'home'
            },
            {
                'key': 'home_feature1_title',
                'title': 'Нүүр - Онцлог 1 гарчиг',
                'content': 'Бясалгал гэж юу вэ?',
                'page': 'home'
            },
            {
                'key': 'home_feature1_desc',
                'title': 'Нүүр - Онцлог 1 тайлбар',
                'content': 'Бид хэрхэн бясалгал хийдэг вэ?',
                'page': 'home'
            },
            {
                'key': 'home_feature2_title',
                'title': 'Нүүр - Онцлог 2 гарчиг',
                'content': 'Ном',
                'page': 'home'
            },
            {
                'key': 'home_feature2_desc',
                'title': 'Нүүр - Онцлог 2 тайлбар',
                'content': 'Хэвлэгдэн гарсан номууд',
                'page': 'home'
            },
            {
                'key': 'home_feature3_title',
                'title': 'Нүүр - Онцлог 3 гарчиг',
                'content': 'Тайлбар үгс',
                'page': 'home'
            },
            {
                'key': 'home_feature3_desc',
                'title': 'Нүүр - Онцлог 3 тайлбар',
                'content': 'Сайтад орсон үгсийн тайлбарууд',
                'page': 'home'
            },
            {
                'key': 'home_about_subtitle',
                'title': 'Нүүр - Бидний тухай дэд гарчиг',
                'content': 'Бясалгалыг сонгох давуу талууд',
                'page': 'home'
            },
            {
                'key': 'home_about_title',
                'title': 'Нүүр - Бидний тухай гарчиг',
                'content': 'Оюун санааны амар амгаланд суралцах болно',
                'page': 'home'
            },
            {
                'key': 'home_about_desc',
                'title': 'Нүүр - Бидний тухай тайлбар',
                'content': 'Бид таньд бясалгалын мэдлэгийг эхнээс зааж, дээд шатны мэдлэгийг шат дараатай системтэйгээр сургах болно.',
                'page': 'home'
            },
            {
                'key': 'home_about_benefit1',
                'title': 'Нүүр - Давуу тал 1',
                'content': 'Гүрү Готопа багш заана',
                'page': 'home'
            },
            {
                'key': 'home_about_benefit2',
                'title': 'Нүүр - Давуу тал 2',
                'content': 'Анхан шатны 3 сарын сургалт: Долоо хоног бүр 2 удаа, 5 цаг орно.',
                'page': 'home'
            },
            {
                'key': 'home_about_benefit3',
                'title': 'Нүүр - Давуу тал 3',
                'content': 'Хичээллэх тав тухтай орчин',
                'page': 'home'
            },
            {
                'key': 'home_about_benefit4',
                'title': 'Нүүр - Давуу тал 4',
                'content': 'Баталгаажсан үр дүн',
                'page': 'home'
            },
        ]

        created_count = 0
        updated_count = 0

        for data in home_contents:
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

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Амжилттай дууслаа! Үүсгэсэн: {created_count}, Шинэчилсэн: {updated_count}'
            )
        )
