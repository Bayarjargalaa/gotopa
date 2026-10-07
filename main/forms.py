import re

from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.db.models import Q


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
