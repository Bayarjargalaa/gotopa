import re

from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.db.models import Q

from .models import Counterparty, Product, ProductCategory


def mask_email(email):
    """Имэйлийн эхний болон сүүлийн хэдэн тэмдэгтийг харуулж, дундахыг нууна: o.b***10@gmail.com"""
    local, _, domain = email.partition('@')
    if len(local) <= 2:
        masked = local[:1] + '*' * (len(local) - 1)
    elif len(local) <= 5:
        masked = local[:1] + '*' * (len(local) - 2) + local[-1:]
    else:
        masked = local[:3] + '*' * (len(local) - 5) + local[-2:]
    return f'{masked}@{domain}'


class PhoneOrEmailPasswordResetForm(PasswordResetForm):
    """Нууц үг сэргээх - утас эсвэл имэйлээр хайж, бүртгэлтэй имэйл рүү линк илгээнэ"""

    email = forms.CharField(label='Утас эсвэл имэйл', max_length=254)

    def _matching_users(self, identifier):
        query = Q(email__iexact=identifier)
        digits = re.sub(r'\D', '', identifier)
        if len(digits) >= 8:
            query |= Q(profile__phone=digits[-8:])
        return User.objects.filter(query, is_active=True).distinct()

    def clean_email(self):
        identifier = self.cleaned_data['email'].strip()
        users = list(self._matching_users(identifier))
        if not users:
            raise forms.ValidationError('Ийм утас эсвэл имэйлтэй хэрэглэгч олдсонгүй.')
        emails = sorted({mask_email(user.email) for user in users if user.email})
        if not emails:
            raise forms.ValidationError(
                f'{identifier} дугаартай хэрэглэгч имэйл бүртгүүлээгүй байна. '
                'Нууц үгээ сэргээхийн тулд менежерт хандана уу.'
            )
        self.masked_emails = emails
        return identifier

    def get_users(self, identifier):
        # Нууц үггүй (харилцагчаас хөрвүүлсэн г.м.) хэрэглэгч ч шинэ нууц үг тохируулж болно
        return self._matching_users(identifier).exclude(email='')


class MoneyField(forms.DecimalField):
    """Мянгатын таслалтай ("12,500") эсвэл зайтай бичсэн дүнг хүлээн авна."""

    def to_python(self, value):
        if isinstance(value, str):
            value = value.replace(',', '').replace(' ', '').replace('₮', '').strip()
        return super().to_python(value)


def product_code_suggestions():
    """Ангилал бүрийн дараагийн барааны код.

    Кодууд ангиллаар 3 оронтой мужид байдаг (Лаа 1xx, Ном 2xx, Шашны эд зүйл 3xx, ...):
    тухайн ангиллын хамгийн их богино тоон кодоос +1, ангилалд код байхгүй бол дараагийн
    чөлөөтэй зуут (500). Тэгээр эхэлсэн ба урт (баркод маягийн) кодыг тооцохгүй.
    Буцаах: ({ангиллын id: код}, ангилалгүй үеийн код, шинэ ангиллын код)
    """
    rows = [(c.strip(), cat) for c, cat in Product.objects.values_list('code', 'category_id')]
    used = {c.casefold() for c, _ in rows}

    def is_short(code):
        return code.isdigit() and not code.startswith('0') and len(code) <= 4

    def free_from(number):
        while str(number) in used:
            number += 1
        return str(number)

    numbers = [int(c) for c, _ in rows if is_short(c)]
    new_block = (max(numbers) // 100 + 1) * 100 if numbers else 100
    by_category = {}
    for code, cat in rows:
        if cat and is_short(code):
            by_category[cat] = max(by_category.get(cat, 0), int(code))
    suggestions = {cat: free_from(top + 1) for cat, top in by_category.items()}
    return suggestions, free_from(max(numbers) + 1 if numbers else 100), free_from(new_block)


def suggest_product_code(category_id=None):
    suggestions, default, new_block = product_code_suggestions()
    if category_id:
        return suggestions.get(category_id, new_block)
    return default


class ProductForm(forms.ModelForm):
    """Бараа нэмэх/засах. Борлуулах үнэ заавал биш (хоосон бол 0 = тогтоогоогүй),
    код хоосон бол автоматаар олгоно."""

    purchase_price = MoneyField(label='Худалдан авах үнэ', min_value=0, max_digits=12, decimal_places=2)
    selling_price = MoneyField(label='Борлуулах үнэ', min_value=0, max_digits=12, decimal_places=2, required=False)

    class Meta:
        model = Product
        fields = ['name', 'code', 'category', 'unit', 'purchase_price', 'selling_price',
                  'initial_stock', 'min_stock', 'supplier_fk', 'description', 'notes', 'image', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['code'].required = False
        self.fields['category'].queryset = ProductCategory.objects.filter(is_active=True).order_by('name')
        self.fields['supplier_fk'].queryset = Counterparty.objects.filter(
            counterparty_type__in=['SUPPLIER', 'BOTH'], is_active=True).order_by('name')
        self.fields['initial_stock'].min_value = 0
        self.fields['initial_stock'].required = False
        self.fields['min_stock'].required = False
        if self.instance.pk:
            # Эхний үлдэгдлийг "Үлдэгдэл" хуудсаар засна
            del self.fields['initial_stock']
        else:
            del self.fields['is_active']

    def clean_name(self):
        return ' '.join(self.cleaned_data['name'].split())

    def clean_code(self):
        code = (self.cleaned_data.get('code') or '').strip()
        if not code:
            category = str(self.data.get('category') or '')
            return suggest_product_code(int(category) if category.isdigit() else None)
        # SQLite iexact кирилл үсгийн том/жижгийг ялгадаг тул Python-д харьцуулна
        others = Product.objects.exclude(pk=self.instance.pk).values_list('code', 'name')
        clash = next((n for c, n in others if c.casefold() == code.casefold()), None)
        if clash is not None:
            raise forms.ValidationError(f'"{code}" код "{clash}" бараанд бүртгэлтэй байна.')
        return code

    def clean_selling_price(self):
        return self.cleaned_data.get('selling_price') or 0

    def clean_initial_stock(self):
        return self.cleaned_data.get('initial_stock') or 0

    def clean_min_stock(self):
        return self.cleaned_data.get('min_stock') or 0
