import html as html_mod
import re
from datetime import date
from decimal import Decimal
from django.db import transaction as db_tx
from django.test import Client
from django.test.utils import override_settings
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from main.models import BankTransaction, ChartOfAccounts, UserProfile, UserRole
from main.import_bank_transactions import regenerate_accounting_entries, delete_cash_transfer_mirrors

admin = User.objects.get(username='gotopa')


def cash_balance():
    qs = BankTransaction.objects.filter(account_type='CASH')
    inc = qs.aggregate(s=Sum('income_amount'))['s'] or Decimal('0')
    exp = qs.aggregate(s=Sum('expense_amount'))['s'] or Decimal('0')
    return inc - exp


print('=== 1. Кассын эсрэг мөр (mirror) ===')
bank_acct = ChartOfAccounts.objects.filter(code__startswith='110', is_active=True).first()
cash_acct = ChartOfAccounts.objects.filter(
    Q(code__startswith='100') | Q(code__startswith='101'), is_active=True).first()
try:
    with db_tx.atomic():
        before = cash_balance()
        bt = BankTransaction.objects.create(
            account_type='BANK', bank_name='KHAN', bank_account=bank_acct,
            transaction_date=date(2026, 8, 18),
            income_amount=Decimal('500000'), expense_amount=Decimal('0'),
            description='VERIFY transfer', offset_account=cash_acct, imported_by=admin,
        )
        regenerate_accounting_entries([bt], admin)
        bt.refresh_from_db()
        m = bt.transfer_mirrors.first()
        print(f'  mirror: {m.account_type} {m.bank_account.code} expense={m.expense_amount} journal={m.accounting_entry_id}')
        print(f'  balance {before} -> {cash_balance()} (expected {before - Decimal("500000")})')
        regenerate_accounting_entries([bt], admin)
        print(f'  re-run mirror count: {bt.transfer_mirrors.count()} (expected 1)')
        print(f'  unlink deletes: {delete_cash_transfer_mirrors(bt)}; balance back to {cash_balance()} (expected {before})')
        raise RuntimeError('ROLLBACK')
except RuntimeError:
    pass
print(f'  final balance unchanged: {cash_balance()}')

print('=== 2. Кирилл хайлт (/students/) ===')
base = UserProfile.objects.filter(role=UserRole.STUDENT)
for term in ('болор', 'БОЛОР', 'БоЛоР'):
    print(f'  {term!r:10} icontains={base.filter(mongolian_name__icontains=term).count()}'
          f'  iucontains={base.filter(mongolian_name__iucontains=term).count()}')

with override_settings(ALLOWED_HOSTS=['testserver']):
    c = Client()
    c.force_login(admin)

    print('=== 3. /students/ хайлт бодит хүсэлтээр ===')
    for term in ('болор', 'БОЛОР', 'БоЛоР'):
        r = c.get('/students/', {'q': term})
        n = len(set(re.findall(r'/students/(\d+)/', r.content.decode('utf-8'))))
        print(f'  q={term!r:10} status={r.status_code} matched={n}')

    print('=== 4. bank-transactions return_to ===')
    list_url = '/finance/bank-transactions/?transaction_type=income&page=2'
    r = c.get(list_url)
    doc = r.content.decode('utf-8')
    links = re.findall(r'/finance/bank-transactions/\d+/link-to-journal/\?return_to=([^"]*)', doc)
    print(f'  list links with return_to: {len(links)}')

    tx = BankTransaction.objects.filter(
        account_type='BANK', income_amount__gt=0, accounting_entry__isnull=True).first()
    r2 = c.get(f'/finance/bank-transactions/{tx.id}/link-to-journal/', {'return_to': list_url})
    vals = {html_mod.unescape(v) for v in re.findall(r'name="return_to" value="([^"]*)"', r2.content.decode('utf-8'))}
    print(f'  link page status={r2.status_code} hidden return_to={vals}')

    offset = ChartOfAccounts.objects.filter(code__startswith='4', is_active=True).first()
    try:
        with db_tx.atomic():
            r3 = c.post(f'/finance/bank-transactions/{tx.id}/link-to-journal/', {
                'offset_account': offset.id, 'return_to': list_url,
            })
            print(f'  POST status={r3.status_code} -> {r3.get("Location")}')
            print(f'  matches filtered page: {r3.get("Location") == list_url}')
            raise RuntimeError('ROLLBACK')
    except RuntimeError:
        pass

    print('=== 5. Шинээр сэргээсэн хуудсууд ===')
    for url in ['/inventory/cost-calculation/', '/finance/journal/', '/finance/cash-transactions/',
                f'/finance/sales/{__import__("main.models", fromlist=["Sale"]).Sale.objects.first().id}/']:
        print(f'  {c.get(url).status_code}  {url}')
