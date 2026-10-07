"""Санхүүгийн үе — "Систем эхлэх огноо" (эхний үлдэгдлийн огноо).

Систем эхлэх огнооноос өмнөх гүйлгээ архивд орно:
- жагсаалт, тайлан, үлдэгдлийн тооцоонд орохгүй;
- зөвхөн superuser архивыг харж, банкны гүйлгээг сурагчийн төлбөрт холбож болно;
- сурагчийн төлбөрийн хуваарилалт (PaymentAllocation) огноо харгалзахгүй харагдана.

Үлдэгдэл = эхний үлдэгдэл (гараар оруулсан) + систем эхлэх огнооноос хойших гүйлгээ.
"""
import time
from decimal import Decimal

_CACHE = {'value': None, 'loaded_at': 0.0}
_CACHE_SECONDS = 30  # gunicorn-ы бусад worker-ууд өөрчлөлтийг ийм хугацаанд авна


def get_books_start_date():
    """Систем эхлэх огноо (date) эсвэл None."""
    now = time.monotonic()
    if now - _CACHE['loaded_at'] > _CACHE_SECONDS:
        from .models import FinanceSettings
        try:
            settings_obj = FinanceSettings.objects.filter(pk=1).only('books_start_date').first()
            _CACHE['value'] = settings_obj.books_start_date if settings_obj else None
        except Exception:
            # Migration хийгдээгүй үед (хүснэгт байхгүй) хязгааргүй гэж үзнэ
            _CACHE['value'] = None
        _CACHE['loaded_at'] = now
    return _CACHE['value']


def clear_start_date_cache():
    _CACHE['loaded_at'] = 0.0


def is_archived_date(value):
    """Огноо систем эхлэх огнооноос өмнө (архивд) байгаа эсэх."""
    start = get_books_start_date()
    if not start or value is None:
        return False
    if hasattr(value, 'date') and callable(value.date):
        from django.utils import timezone
        value = timezone.localtime(value).date() if timezone.is_aware(value) else value.date()
    return value < start


def counts_in_balances(value):
    """Энэ огнооны бичилт дансны үлдэгдэлд тооцогдох эсэх."""
    return not is_archived_date(value)


def can_view_archive(user):
    return bool(user and user.is_authenticated and user.is_superuser)


def wants_archive(request):
    """?archive=1 — зөвхөн superuser-д зөвшөөрнө."""
    return request.GET.get('archive') == '1' and can_view_archive(request.user)


def period_filter(queryset, date_field, archive=False):
    """queryset-ийг шинэ үе (эсвэл archive=True бол архив)-ээр шүүнэ."""
    start = get_books_start_date()
    if not start:
        return queryset.none() if archive else queryset
    lookup = f'{date_field}__lt' if archive else f'{date_field}__gte'
    return queryset.filter(**{lookup: start})


def current_period_movements(queryset):
    """Барааны хөдөлгөөн (created_at — орон нутгийн огноогоор) шинэ үеийнх."""
    return period_filter(queryset, 'created_at__date')


def recalculate_account_balances():
    """Дансны дебит/кредит үлдэгдлийг шинэ үеийн журналаас дахин тооцоолно."""
    from django.db.models import Sum
    from .models import AccountingEntry, ChartOfAccounts

    entries = period_filter(AccountingEntry.objects.all(), 'entry_date')
    debits = dict(entries.values('debit_account').annotate(s=Sum('debit_amount')).values_list('debit_account', 's'))
    credits = dict(entries.values('credit_account').annotate(s=Sum('credit_amount')).values_list('credit_account', 's'))

    changed = 0
    for account in ChartOfAccounts.objects.all():
        debit = debits.get(account.id) or Decimal('0')
        credit = credits.get(account.id) or Decimal('0')
        if account.debit_balance != debit or account.credit_balance != credit:
            account.debit_balance = debit
            account.credit_balance = credit
            account.save(update_fields=['debit_balance', 'credit_balance'])
            changed += 1
    return changed


def archived_denied(request, value, redirect_to):
    """Архивын бүртгэлийг superuser-ээс бусад нь өөрчлөх/харахыг хориглоно.

    Хориглосон бол redirect response, үгүй бол None буцаана.
    """
    if is_archived_date(value) and not can_view_archive(request.user):
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(
            request,
            f'Энэ бүртгэл систем эхлэх огнооноос ({get_books_start_date():%Y-%m-%d}) өмнөх тул архивд орсон. '
            'Зөвхөн superuser өөрчилнө.'
        )
        return redirect(redirect_to)
    return None


def closed_period_error(request, value):
    """Шинэ бүртгэл систем эхлэх огнооноос өмнөх огноотой бол алдааны текст (superuser-д зөвшөөрнө)."""
    if is_archived_date(value) and not can_view_archive(request.user):
        return (f'Огноо систем эхлэх огнооноос ({get_books_start_date():%Y-%m-%d}) өмнө байж болохгүй. '
                'Тэр хугацааны үлдэгдлийг эхний үлдэгдлээр оруулна.')
    return None
