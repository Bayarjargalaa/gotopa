import re
from django.test import Client
from django.test.utils import override_settings
from django.contrib.auth.models import User
from django.urls import reverse, get_resolver
from main.models import BankTransaction, Sale, StockMovement, ChartOfAccounts, AccountingEntry, Product, UserProfile

admin = User.objects.get(username='gotopa')

# Бүх GET-ээр дуудагдах URL-уудыг автоматаар цуглуулна
import main.urls as main_urls
sample_ids = {
    'transaction_id': (BankTransaction.objects.filter(account_type='CASH').first() or BankTransaction.objects.first()).id,
    'sale_id': Sale.objects.first().id,
    'movement_id': (StockMovement.objects.filter(sale__isnull=True).first() or StockMovement.objects.first()).id,
    'account_id': ChartOfAccounts.objects.first().id,
    'entry_id': AccountingEntry.objects.first().id,
    'product_id': Product.objects.first().id,
    'student_id': UserProfile.objects.filter(role='STUDENT').first().id,
    'course_id': 1,
    'teacher_id': 1,
    'enrollment_id': 1,
    'counterparty_id': 1,
    'user_id': admin.id,
    'group_id': 1,
}

# Устгах/POST-only үйлдлүүдийг GET-ээр дуудахгүй
skip = {
    'user_logout', 'student_delete', 'teacher_delete', 'course_delete',
    'journal_delete', 'chart_account_delete', 'chart_account_delete_empty',
    'counterparty_delete', 'group_delete', 'purchase_delete', 'sale_delete',
    'sale_finance_delete', 'cash_transaction_delete', 'unlink_bank_transaction',
    'journal_unlink_transactions', 'sale_link_expense', 'sale_link_bank',
    'enrollment_approve', 'enrollment_reject', 'product_set_initial_stock',
    'update_page_content', 'attendance_mark',
}

ok = 0
bad = []
with override_settings(ALLOWED_HOSTS=['testserver'], DEBUG_PROPAGATE_EXCEPTIONS=False):
    c = Client(raise_request_exception=False)
    c.force_login(admin)
    for pattern in main_urls.urlpatterns:
        name = getattr(pattern, 'name', None)
        if not name or name in skip:
            continue
        keys = list(getattr(pattern.pattern, 'converters', {}).keys())
        try:
            args = [sample_ids[k] for k in keys]
        except KeyError:
            continue
        try:
            url = reverse(f'main:{name}', args=args)
        except Exception as e:
            bad.append((name, f'reverse failed: {e}'))
            continue
        r = c.get(url)
        if r.status_code >= 500:
            bad.append((name, f'{r.status_code} {url}'))
        else:
            ok += 1

print(f'OK (<500): {ok}')
print(f'FAILING: {len(bad)}')
for name, info in bad:
    print('  ', name, '->', info)
