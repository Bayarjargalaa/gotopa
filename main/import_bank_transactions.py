"""
Банкны хуулгын файлаас гүйлгээг импортлох (Хаан болон Голомт банк)

Дэмжигдсэн форматууд:

1. Хаан банк:
   Гүйлгээний огноо | Салбар | Эхний үлдэгдэл | Дебит гүйлгээ | Кредит гүйлгээ | Эцсийн үлдэгдэл | Гүйлгээний утга | Харьцсан данс

2. Голомт банк:
   Гүйлгээний огноо | Гүйлгээний утга | Харьцсан дансны нэр | Харьцсан данс | Ханш | Орлого | Зарлага

3. Хас банк:
   Огноо | Гүйлгээний утга | Харьцсан данс | Гүйлгээний дугаар | Орлого | Зарлага | Үлдэгдэл
"""

import pandas as pd
from main.models import BankTransaction, AccountingEntry, ChartOfAccounts, Counterparty
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.utils import timezone
from django.db import IntegrityError, transaction


def next_entry_number(stem, width=4):
    """`stem`-ээр эхэлсэн журналын дугааруудын дараах дараалалыг буцаана

    Дугаарыг НИЙТ ТООГООР бодохгүй, байгаа дугааруудын ХАМГИЙН ИХ дараалал дээр
    нэмж бодно. Устгагдсан бичилтээс болж дугаарлалтад цоорхой үүссэн үед
    (жишээ нь BNK20260120: 1..14, 16) тоогоор бодох нь аль хэдийн байгаа
    дугаарыг дахин үүсгэж `UNIQUE constraint failed` алдаа гаргадаг байсан.

    Args:
        stem: дугаарын угтвар (жишээ 'BNK20260120', 'PUR-20260120-')
        width: дарааллын оронгийн тоо (default 4 → 0001)

    Returns:
        (seq, entry_number) хос
    """
    import re

    pattern = re.compile(rf'^{re.escape(stem)}(\d+)')
    max_seq = 0
    for existing in AccountingEntry.objects.filter(
        entry_number__startswith=stem
    ).values_list('entry_number', flat=True):
        match = pattern.match(existing or '')
        if match:
            seq = int(match.group(1))
            if seq > max_seq:
                max_seq = seq

    next_seq = max_seq + 1
    return next_seq, f'{stem}{next_seq:0{width}d}'


def create_accounting_entry_safe(**kwargs):
    """Module-level helper to create AccountingEntry with basic retry on IntegrityError.

    This function attempts to create an AccountingEntry and, if a UNIQUE
    constraint failure happens on `entry_number`, recomputes a sequence-based
    number for prefixes like BNKYYYYMMDD or CSHYYYYMMDD and retries. As a
    fallback it appends a short random suffix to guarantee uniqueness.
    """
    import re
    import uuid
    max_tries = 10
    last_exc = None
    for _ in range(max_tries):
        try:
            with transaction.atomic():
                return AccountingEntry.objects.create(**kwargs)
        except IntegrityError as e:
            last_exc = e
            en = kwargs.get('entry_number', '')
            m = re.match(r'^(?P<prefix>[A-Z]+)(?P<date>\d{8})(?P<seq>\d+)', en)
            if m:
                stem = f"{m.group('prefix')}{m.group('date')}"
                _, candidate = next_entry_number(stem, width=len(m.group('seq')))
                # Дугаар өөрчлөгдөөгүй бол дахин мөн адил алдаа гарах тул
                # давхардахгүй санамсаргүй дагаваар шилжинэ
                if candidate != en:
                    kwargs['entry_number'] = candidate
                    continue
            suffix = uuid.uuid4().hex[:6].upper()
            kwargs['entry_number'] = f"{en}-{suffix}"
            continue
    # If we exit loop without returning, re-raise the last caught exception
    if last_exc:
        raise last_exc
    raise IntegrityError('Failed to create AccountingEntry after retries')


SALE_REVENUE_CODE = '510101'


def sync_sale_revenue_journal(bt, user, dry_run=False):
    """Борлуулалтад холбогдсон гүйлгээний орлогын журналыг тэнцүүлэх

    Бичилт: Дт банк/касс — Кт 510101 Борлуулалтын орлого, дүн нь борлуулалтад
    хуваарилагдсан нийт дүн. Борлуулалтад холбоход журнал шууд үүсч, эсрэг данс
    бөглөгдөнө; хуваарилалт өөрчлөгдөхөд дүн шинэчлэгдэж, бүх холбоос тасрахад
    бичилт устгагдана.

    Сурагчийн төлбөртэй хамт хуваарилагдсан (хосолсон) гүйлгээг хөндөхгүй —
    түүнийг нягтлан "журналд холбох" хуудсаар гараар ангилна. Мөн 510101-ээс
    өөр данс руу гараар ангилсан бичилтийг ч дарж бичихгүй.

    Args:
        dry_run: True бол өгөгдлийг хөндөхгүй, зөвхөн юу болохыг буцаана

    Returns:
        str: 'created' | 'updated' | 'offset' | 'deleted' | 'skipped'
    """
    from decimal import Decimal
    from django.db.models import Sum

    # Автоматаар үүссэн кассын эсрэг мөр өөрөө журнал үүсгэхгүй
    if bt.transfer_source_id:
        return 'skipped'

    student_alloc = bt.allocations.aggregate(s=Sum('amount'))['s'] or Decimal('0')
    sale_alloc = bt.sale_allocations.aggregate(s=Sum('amount'))['s'] or Decimal('0')

    # Legacy бүрэн холбоос (income_sale) — гүйлгээний дүн бүхэлдээ борлуулалтад тооцогдоно
    if sale_alloc == 0 and bt.income_sale_id:
        sale_alloc = bt.income_amount or Decimal('0')

    # Хосолсон хуваарилалт (сурагчийн төлбөр + борлуулалт): сурагчийн ангиллыг нягтлан
    # хийсэн бол хоёр хэсгийг тусад нь бичнэ, эс бөгөөс гараар ангилуулна
    if student_alloc > 0:
        if bt.offset_account_id and not dry_run:
            sync_mixed_income_journal(bt, user)
            return 'updated'
        return 'skipped'

    # Өмнө нь хосолсон байсан (сурагчийн хэсэг нь цуцлагдсан) — хоёр бичилтийг цэвэрлээд
    # доорх энгийн борлуулалтын журнал руу шилжинэ
    if bt.sale_revenue_entry_id and not dry_run:
        drop_entry(bt, 'sale_revenue_entry')
        drop_entry(bt, 'accounting_entry')
        bt.offset_account = None
        bt.save(update_fields=['offset_account'])

    revenue_account = ChartOfAccounts.objects.filter(code=SALE_REVENUE_CODE).first()
    if not revenue_account or not bt.bank_account_id:
        return 'skipped'

    entry = bt.accounting_entry
    # Зөвхөн өөрсдөө үүсгэсэн (Кт 510101, Дт тухайн банк/касс) бичилтийг хөндөнө
    is_own_entry = bool(
        entry and
        entry.credit_account_id == revenue_account.id and
        entry.debit_account_id == bt.bank_account_id
    )

    if sale_alloc <= 0:
        # Холбоос бүрэн тасарсан — өөрсдөө үүсгэсэн бичилтийг цэвэрлэнэ
        if is_own_entry and not bt.income_sale_id:
            if dry_run:
                return 'deleted'
            bt.accounting_entry = None
            bt.offset_account = None
            bt.is_processed = False
            bt.save(update_fields=['accounting_entry', 'offset_account', 'is_processed'])
            entry.delete()
            return 'deleted'
        return 'skipped'

    if entry and not is_own_entry:
        # Гараар өөр дансаар ангилсан байна — хөндөхгүй
        return 'skipped'

    fully_posted = sale_alloc >= (bt.income_amount or 0)
    needs_offset = bt.offset_account_id != revenue_account.id
    needs_processed = bt.is_processed != fully_posted

    if dry_run:
        if not is_own_entry:
            return 'created'
        if entry.debit_amount != sale_alloc or entry.credit_amount != sale_alloc:
            return 'updated'
        if needs_offset or needs_processed:
            return 'offset'
        return 'skipped'

    update_fields = []
    result = 'skipped'

    if is_own_entry:
        if entry.debit_amount != sale_alloc or entry.credit_amount != sale_alloc:
            entry.debit_amount = sale_alloc
            entry.credit_amount = sale_alloc
            entry.save()
            result = 'updated'
    else:
        date_key = bt.transaction_date.strftime('%Y%m%d')
        prefix = 'CSH' if bt.account_type == 'CASH' else 'BNK'
        _, entry_number = next_entry_number(f'{prefix}{date_key}')

        linked_sales = [alloc.sale for alloc in bt.sale_allocations.select_related('sale')]
        entry = create_accounting_entry_safe(
            entry_date=bt.transaction_date,
            entry_number=entry_number,
            description=bt.description,
            debit_account=bt.bank_account,
            debit_amount=sale_alloc,
            credit_account=revenue_account,
            credit_amount=sale_alloc,
            created_by=user,
            related_sale=linked_sales[0] if len(linked_sales) == 1 else None,
        )
        bt.accounting_entry = entry
        update_fields.append('accounting_entry')
        result = 'created'

    if needs_offset:
        bt.offset_account = revenue_account
        update_fields.append('offset_account')

    # Гүйлгээний дүн бүхэлдээ борлуулалтад хуваарилагдсан бол л журналд орсонд тооцно
    if needs_processed:
        bt.is_processed = fully_posted
        update_fields.append('is_processed')

    if update_fields:
        bt.save(update_fields=update_fields)
        if result == 'skipped':
            result = 'offset'

    return result


def drop_entry(bt, field):
    """Гүйлгээнээс журналын бичилтийг салгаж устгана (дансны үлдэгдэл буцна).

    Эхлээд холбоосыг салгана: AccountingEntry.delete() нь accounting_entry-ээр
    холбогдсон гүйлгээний хуваарилалтуудыг устгадаг тул.
    """
    entry = getattr(bt, field)
    if entry is None:
        return
    setattr(bt, field, None)
    bt.save(update_fields=[field])
    entry.delete()


def sync_mixed_income_journal(bt, user):
    """Сурагчийн төлбөр + борлуулалтад хуваагдсан орлогын гүйлгээний журнал.

    Нэг гүйлгээний орлого хоёр өөр орлогын дансанд хуваагдана (жишээ нь POS сэттлмэнт —
    борлуулалт 152,000, сургалтын төлбөр 1,000,000):
      accounting_entry   = Дт банк / Кт эсрэг данс (сургалтын орлого) — сурагчийн хэсэг
      sale_revenue_entry = Дт банк / Кт 510101 Борлуулалтын орлого     — борлуулалтын хэсэг
    Хуваарилалт өөрчлөгдөх бүрт хоёуланг дахин үүсгэнэ.
    """
    from decimal import Decimal
    from django.db import transaction as db_transaction
    from django.db.models import Sum

    student = bt.allocations.aggregate(s=Sum('amount'))['s'] or Decimal('0')
    sale = bt.sale_allocations.aggregate(s=Sum('amount'))['s'] or Decimal('0')
    revenue_account = ChartOfAccounts.objects.filter(code=SALE_REVENUE_CODE).first()
    if not bt.bank_account_id or not revenue_account:
        return

    date_key = bt.transaction_date.strftime('%Y%m%d')
    prefix = 'CSH' if bt.account_type == 'CASH' else 'BNK'

    def create(credit_account, amount):
        _, number = next_entry_number(f'{prefix}{date_key}')
        return create_accounting_entry_safe(
            entry_date=bt.transaction_date, entry_number=number, description=bt.description,
            debit_account=bt.bank_account, debit_amount=amount,
            credit_account=credit_account, credit_amount=amount, created_by=user,
        )

    with db_transaction.atomic():
        drop_entry(bt, 'accounting_entry')
        drop_entry(bt, 'sale_revenue_entry')
        if student > 0 and bt.offset_account_id:
            bt.accounting_entry = create(bt.offset_account, student)
        if sale > 0:
            bt.sale_revenue_entry = create(revenue_account, sale)
        bt.is_processed = bool(bt.accounting_entry_id) and student + sale >= (bt.income_amount or 0)
        bt.save(update_fields=['accounting_entry', 'sale_revenue_entry', 'is_processed'])


def is_cash_account(account):
    """Данс нь кассын данс эсэх (100x, 101x код)"""
    if not account or not account.code:
        return False
    return account.code.startswith('100') or account.code.startswith('101')


def sync_cash_transfer_mirrors(bt, user):
    """Эсрэг данс нь касс байх үед кассын эсрэг талын гүйлгээг автоматаар үүсгэх/шинэчлэх

    Кассын үлдэгдэл нь `account_type='CASH'` бүхий BankTransaction мөрүүдээс тооцогддог
    тул харилцахын гүйлгээг касс дансаар холбоход журнал төдийгүй кассын мөр ч
    үүсэх шаардлагатай. Ингэснээр кассын үлдэгдэл зөв хасагдана/нэмэгдэнэ.

    Эсрэг мөр нь өөрийн журналын бичилт үүсгэхгүй (accounting_entry=None), учир нь
    журналыг эх гүйлгээ өөрөө үүсгэсэн байна — давхар бичилт гарахаас сэргийлнэ.
    """
    from decimal import Decimal

    # Эсрэг мөр өөрөө дахин эсрэг мөр үүсгэхгүй
    if bt.transfer_source_id:
        return

    # Кассын данс тус бүрт очих дүнг цуглуулах (үндсэн эсрэг данс + нэмэлт хуваарилалтууд)
    per_cash_account = {}

    try:
        extra_splits = list(bt.extra_splits.all())
    except Exception:
        extra_splits = []
    extra_total = sum(s.amount for s in extra_splits) if extra_splits else Decimal('0')

    income = bt.income_amount or Decimal('0')
    expense = bt.expense_amount or Decimal('0')
    main_amount = (income - extra_total) if income > 0 else (expense - extra_total)

    if (
        is_cash_account(bt.offset_account)
        and bt.offset_account_id != bt.bank_account_id
        and main_amount > 0
    ):
        per_cash_account[bt.offset_account_id] = (
            per_cash_account.get(bt.offset_account_id, Decimal('0')) + main_amount
        )

    for split in extra_splits:
        if (
            is_cash_account(split.account)
            and split.account_id != bt.bank_account_id
            and split.amount > 0
        ):
            per_cash_account[split.account_id] = (
                per_cash_account.get(split.account_id, Decimal('0')) + split.amount
            )

    existing_mirrors = {m.bank_account_id: m for m in bt.transfer_mirrors.all()}

    # Шаардлагагүй болсон эсрэг мөрүүдийг устгах
    for account_id, mirror in existing_mirrors.items():
        if account_id not in per_cash_account:
            mirror.delete()

    # Орлого бол касснаас гарсан (зарлага), зарлага бол касс руу орсон (орлого)
    for account_id, amount in per_cash_account.items():
        mirror_income = Decimal('0') if income > 0 else amount
        mirror_expense = amount if income > 0 else Decimal('0')

        mirror = existing_mirrors.get(account_id)
        if mirror is None:
            mirror = BankTransaction(
                transfer_source=bt,
                account_type='CASH',
                bank_name='CASH_REGISTER',
                bank_account_id=account_id,
                imported_by=user,
            )

        mirror.transaction_date = bt.transaction_date
        mirror.description = bt.description
        mirror.income_amount = mirror_income
        mirror.expense_amount = mirror_expense
        mirror.offset_account = bt.bank_account
        mirror.cash_flow_indicator_id = bt.cash_flow_indicator_id
        mirror.accounting_entry = None  # Журналыг эх гүйлгээ үүсгэсэн
        mirror.is_processed = True
        mirror.save()


def delete_cash_transfer_mirrors(bt):
    """Гүйлгээний холболт цуцлагдах үед автоматаар үүссэн кассын эсрэг мөрүүдийг устгах"""
    if bt.transfer_source_id:
        return 0
    deleted = 0
    for mirror in bt.transfer_mirrors.all():
        mirror.delete()
        deleted += 1
    return deleted


def link_bank_transfer(expense_tx, income_tx, user):
    """Хоёр өөр харилцахын бодит гүйлгээг (зарлага ба орлого) дотоод шилжүүлэг
    болгон холбож, ганц журналын бичилт үүсгэнэ: Дт хүлээн авагч харилцах / Кт эх харилцах.

    Хоёр тал хоёулаа өөрсдийн банкны хуулгаас аль хэдийн импортлогдсон бодит мөр тул
    `sync_cash_transfer_mirrors`-ийн адил шинэ мөр үүсгэдэггүй — зөвхөн холбоно.
    """
    from .models import BankTransferLink

    amount = expense_tx.expense_amount
    date_key = expense_tx.transaction_date.strftime('%Y%m%d')
    _, entry_number = next_entry_number(f'XFR{date_key}')

    entry = create_accounting_entry_safe(
        entry_date=expense_tx.transaction_date,
        entry_number=entry_number,
        description=f'Харилцах хоорондын шилжүүлэг: {expense_tx.bank_account.name} → {income_tx.bank_account.name}',
        debit_account=income_tx.bank_account,
        debit_amount=amount,
        credit_account=expense_tx.bank_account,
        credit_amount=amount,
        created_by=user,
    )

    expense_tx.accounting_entry = entry
    expense_tx.offset_account = income_tx.bank_account
    expense_tx.is_processed = True
    expense_tx.save(update_fields=['accounting_entry', 'offset_account', 'is_processed'])

    income_tx.accounting_entry = entry
    income_tx.offset_account = expense_tx.bank_account
    income_tx.is_processed = True
    income_tx.save(update_fields=['accounting_entry', 'offset_account', 'is_processed'])

    return BankTransferLink.objects.create(
        expense_transaction=expense_tx,
        income_transaction=income_tx,
        accounting_entry=entry,
        amount=amount,
        created_by=user,
    )


def unlink_bank_transfer(bt):
    """Шилжүүлгийн холбоосыг тасалж, түүний журналын бичилтийг устгана.

    Returns:
        bool: холбоос олдож цуцлагдсан бол True
    """
    from .models import BankTransferLink
    from django.db.models import Q as _Q

    link = BankTransferLink.objects.filter(
        _Q(expense_transaction=bt) | _Q(income_transaction=bt)
    ).select_related('expense_transaction', 'income_transaction', 'accounting_entry').first()
    if not link:
        return False

    entry = link.accounting_entry
    for side in (link.expense_transaction, link.income_transaction):
        side.accounting_entry = None
        side.offset_account = None
        side.is_processed = False
        side.save(update_fields=['accounting_entry', 'offset_account', 'is_processed'])

    link.delete()
    if entry:
        entry.delete()
    return True


def detect_bank_format(df):
    """Банкны хуулгын форматыг баганын нэрээс таних"""
    columns = [str(col).strip() for col in df.columns]

    if {'Огноо', 'Гүйлгээний дугаар', 'Орлого', 'Зарлага', 'Үлдэгдэл'} <= set(columns):
        return 'xac'
    
    if 'Дебит гүйлгээ' in columns and 'Кредит гүйлгээ' in columns:
        return 'khan'
    
    if 'Орлого' in columns and 'Зарлага' in columns:
        return 'golomt'
    
    return None



class BankImportError(Exception):
    """Хэрэглэгчид харуулах импортын алдаа (файлыг бүхэлд нь импортлохгүй)"""


def _parse_xac_amount(value):
    """'5,000,000.00' / '-' / хоосон → Decimal"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return Decimal('0')
    text = str(value).replace(',', '').replace(' ', '').strip()
    if text in ('', '-', 'nan'):
        return Decimal('0')
    return Decimal(text)


def _parse_xac_date(value):
    if hasattr(value, 'to_pydatetime'):
        return value.to_pydatetime().date()
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    for fmt in ('%Y-%m-%d', '%Y.%m.%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _split_xac_counterparty(text):
    """'БОЛОР БАТСҮРЭН ХААН БАНК-5039139089' → ('БОЛОР БАТСҮРЭН ХААН БАНК', '5039139089')"""
    text = (text or '').strip()
    if not text or text == 'nan':
        return '', ''
    name, sep, account = text.rpartition('-')
    if sep and account.strip().isdigit():
        return name.strip(), account.strip()
    return text, ''


def _read_xac_header_info(excel_file):
    """Хуулгын толгой хэсгээс дансны дугаар, хугацааг унших"""
    info = {}
    preview = pd.read_excel(excel_file, engine='openpyxl', header=None, nrows=10, dtype=str)
    labels = {'Дансны дугаар:': 'account_number', 'Эхлэх:': 'start', 'Дуусах:': 'end'}
    for _, row in preview.iterrows():
        cells = [str(c).strip() for c in row.tolist()]
        for i, cell in enumerate(cells[:-1]):
            if cell in labels and cells[i + 1] not in ('', 'nan'):
                info[labels[cell]] = cells[i + 1]
    return info


def import_xac_statement(df, bank_account, header_info=None):
    """Хас банкны хуулга импортлох

    Багана: Огноо | Гүйлгээний утга | Харьцсан данс | Гүйлгээний дугаар | Орлого | Зарлага | Үлдэгдэл

    Давхардал: шилжүүлэг болон түүний шимтгэл ижил гүйлгээний дугаартай ирдэг тул
    (огноо, гүйлгээний дугаар, орлого, зарлага)-аар шалгана. Гүйлгээний дараах үлдэгдлийг
    түлхүүрт оруулахгүй: хуулгад цаг байхгүй тул нэг өдрийн мөрүүдийн (жишээ нь сэттлмэнт,
    шимтгэл) дарааллыг банк татах бүрт өөрөөр гаргаж, үлдэгдэл нь өөр гардаг — үүнээс болж
    давхцсан хуулгыг дахин импортлоход гүйлгээ давхардаж байсан. Ижил түлхүүртэй хэд хэдэн
    жинхэнэ мөр байж болох тул файлд N дахь удаа гарсан мөрийг DB-д N-ээс цөөн байвал л үүсгэнэ.
    """
    header_info = header_info or {}
    rows = []
    errors = []
    warnings = []
    opening_balance = None

    for index, row in df.iterrows():
        excel_row = index + 2 + df.attrs.get('header_row', 0)
        description = str(row.get('Гүйлгээний утга', '') or '').strip()
        if description == 'nan':
            description = ''
        balance_raw = row.get('Үлдэгдэл')

        # Эхний/эцсийн үлдэгдлийн мөр
        if description == 'Эхний үлдэгдэл':
            opening_balance = _parse_xac_amount(balance_raw)
            continue
        if description == 'Эцсийн үлдэгдэл':
            continue

        reference = str(row.get('Гүйлгээний дугаар', '') or '').strip()
        date_raw = row.get('Огноо')
        if not reference or reference == 'nan' or date_raw is None or (isinstance(date_raw, float) and pd.isna(date_raw)):
            continue  # Хуулгын хөл (хэвлэсэн огноо г.м.)

        transaction_date = _parse_xac_date(date_raw)
        try:
            income = _parse_xac_amount(row.get('Орлого'))
            expense = _parse_xac_amount(row.get('Зарлага'))
            balance = _parse_xac_amount(balance_raw) if str(balance_raw).strip() not in ('', 'nan', 'None') else None
        except InvalidOperation:
            errors.append(f'Мөр {excel_row}: дүн буруу ({row.get("Орлого")} / {row.get("Зарлага")})')
            continue
        if transaction_date is None:
            errors.append(f'Мөр {excel_row}: огноо буруу ({date_raw})')
            continue
        if income and expense:
            errors.append(f'Мөр {excel_row}: орлого, зарлага хоёулаа бөглөгдсөн')
            continue
        if not income and not expense:
            continue

        counterparty_name, counterparty_account = _split_xac_counterparty(str(row.get('Харьцсан данс', '') or ''))
        rows.append({
            'excel_row': excel_row,
            'date': transaction_date,
            'reference': reference,
            'description': description or 'Банкны гүйлгээ',
            'counterparty_name': counterparty_name,
            'counterparty_account': counterparty_account,
            'income': income,
            'expense': expense,
            'balance': balance,
        })

    if errors:
        raise BankImportError('Файлд алдаатай мөр байна, юу ч импортлоогүй:\n' + '\n'.join(errors[:10]))
    if not rows:
        raise BankImportError('Хас банкны хуулгаас гүйлгээ олдсонгүй.')

    # Үлдэгдлийн уялдаа: өмнөх үлдэгдэл + орлого - зарлага = үлдэгдэл (файл дутуу/буруу уншигдсан эсэх)
    running = opening_balance
    for r in rows:
        if running is not None and r['balance'] is not None:
            expected = running + r['income'] - r['expense']
            if abs(expected - r['balance']) >= Decimal('0.01'):
                warnings.append(
                    f"Мөр {r['excel_row']}: үлдэгдэл таарахгүй байна "
                    f"(хүлээгдэж буй {expected:,.2f}, хуулгад {r['balance']:,.2f})"
                )
        running = r['balance'] if r['balance'] is not None else None

    def dedup_filter(r):
        return {
            'bank_name': 'XAC',
            'reference_number': r['reference'],
            'transaction_date': r['date'],
            'income_amount': r['income'],
            'expense_amount': r['expense'],
        }

    created_count = 0
    skipped_count = 0
    other_account_count = 0
    file_occurrences = {}

    with transaction.atomic():
        for r in rows:
            key = tuple(dedup_filter(r).values())
            occurrence = file_occurrences.get(key, 0)
            file_occurrences[key] = occurrence + 1

            matches = BankTransaction.objects.filter(**dedup_filter(r))
            if matches.count() > occurrence:
                skipped_count += 1
                if not matches.filter(bank_account=bank_account).exists():
                    other_account_count += 1
                continue

            counterparty = None
            if r['counterparty_name']:
                counterparty, _ = Counterparty.objects.get_or_create(
                    name=r['counterparty_name'],
                    defaults={'counterparty_type': 'BOTH'}
                )

            BankTransaction.objects.create(
                account_type='BANK',
                bank_name='XAC',
                bank_account=bank_account,
                transaction_date=r['date'],
                description=r['description'],
                reference_number=r['reference'],
                counterparty_account=r['counterparty_account'],
                counterparty_name=r['counterparty_name'],
                counterparty=counterparty,
                income_amount=r['income'],
                expense_amount=r['expense'],
                closing_balance=r['balance'],
                opening_balance=(r['balance'] - r['income'] + r['expense']) if r['balance'] is not None else None,
                is_processed=False,
                offset_account=None,
            )
            created_count += 1

    if other_account_count:
        warnings.insert(0, f'{other_account_count} гүйлгээ өөр дансанд аль хэдийн импортлогдсон тул алгаслаа. '
                           f'Зөв данс сонгосон эсэхээ шалгана уу.')

    return {
        'bank': 'Хас банк',
        'created': created_count,
        'skipped': skipped_count,
        'final_balance': bank_account.balance,
        'statement_account': header_info.get('account_number', ''),
        'period': f"{header_info.get('start', '')} – {header_info.get('end', '')}".strip(' –'),
        'warnings': warnings,
    }


def import_bank_transactions(excel_file, bank_account):
    """Банкны хуулгын файлаас гүйлгээг импортлох
    
    Args:
        excel_file: Excel файлын path эсвэл file object
        bank_account: ChartOfAccounts объект (банкны данс)
    """
    try:
        print(f"✓ Данс: {bank_account.code} - {bank_account.name} (Үлдэгдэл: {bank_account.balance:,.0f}₮)")
        
        # Excel унших - эхний мөрнүүдийг алгасах (Хаан банкны тайлбар мэдээлэл)
        # Эхлээд бүх файлыг уншиж, header-г хаанаас эхлэхийг олох
        df_preview = pd.read_excel(excel_file, engine='openpyxl', header=None, nrows=30)
        
        # "Гүйлгээний огноо" гэсэн баганыг хайх (header мөр)
        header_row = None
        for idx, row in df_preview.iterrows():
            cells = [str(cell).strip() for cell in row]
            # "Гүйлгээний огноо" (Хаан, Голомт) эсвэл "Огноо" + "Гүйлгээний дугаар" (Хас)
            if any('Гүйлгээний огноо' in cell for cell in cells) or \
                    ('Огноо' in cells and 'Гүйлгээний дугаар' in cells):
                header_row = idx
                break
        
        # Header олдсон бол тэр мөрийг header болгон унших
        if header_row is not None:
            print(f"✓ Header олдлоо: мөр {header_row + 1}")
            df = pd.read_excel(excel_file, engine='openpyxl', header=header_row)
        else:
            print("⚠️ Header олдсонгүй, анхны мөрөөр оролдож байна...")
            df = pd.read_excel(excel_file, engine='openpyxl')
        
        print(f"\nНийт мөр: {len(df)}")
        print(f"Баганууд: {list(df.columns)[:5]}...")  # Эхний 5 баганыг харуулах
        
        # Формат таних
        bank_format = detect_bank_format(df)
        if not bank_format:
            print("✗ Танигдаагүй банкны формат!")
            print(f"Бүх баганууд: {list(df.columns)}")
            return None

        if bank_format == 'xac':
            # Хас банкны дүн "5,000,000.00" текстээр ирдэг тул бүгдийг текстээр уншина
            df = pd.read_excel(excel_file, engine='openpyxl', header=header_row, dtype=str)
            df.columns = [str(col).strip() for col in df.columns]
            df.attrs['header_row'] = header_row or 0
            return import_xac_statement(df, bank_account, _read_xac_header_info(excel_file))
        
        print(f"✓ Банк: {'Хаан банк' if bank_format == 'khan' else 'Голомт банк'}\n")
        
        created_count = 0
        skipped_count = 0
        file_occurrences = {}  # {давхардлын түлхүүр: файлд хэдэн удаа гарсан}

        # Өдөр бүрийн дугаарлалтын tracker (entry_number давхцахгүйн тулд)
        daily_entry_counts = {}  # {YYYYMMDD: max_sequence_number}
        
        for index, row in df.iterrows():
            try:
                # Огноо
                transaction_date = row.get('Гүйлгээний огноо')
                if pd.isna(transaction_date):
                    skipped_count += 1
                    continue
                
                # Огноо форматлах - Pandas нь datetime/Timestamp object болгон уншдаг
                if isinstance(transaction_date, str):
                    # String байвал янз бүрийн форматаар оролдох (секундгүй ISO формат нэмсэн)
                    parsed = False
                    for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d.%m.%Y', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S']:
                        try:
                            transaction_date = datetime.strptime(transaction_date, fmt)
                            parsed = True
                            break
                        except:
                            continue
                    
                    if not parsed:
                        error_msg = f"❌ Мөр {index + 2}: Огноо буруу форматтай '{transaction_date}' - Дэмжигдсэн форматууд: YYYY-MM-DDTHH:MM:SS, YYYY-MM-DDTHH:MM, YYYY-MM-DD, YYYY/MM/DD, DD/MM/YYYY"
                        print(error_msg)
                        raise ValueError(error_msg)
                elif hasattr(transaction_date, 'to_pydatetime'):
                    # Pandas Timestamp object бол Python datetime руу хөрвүүлэх
                    transaction_date = transaction_date.to_pydatetime()
                elif not isinstance(transaction_date, datetime):
                    # datetime биш бол error шидэх
                    error_msg = f"❌ Мөр {index + 2}: Огноо буруу төрөлтэй '{type(transaction_date).__name__}' - Огноо байх ёстой"
                    print(error_msg)
                    raise ValueError(error_msg)
                
                # Timezone оруулах
                transaction_date = timezone.make_aware(transaction_date) if timezone.is_naive(transaction_date) else transaction_date
                
                # Банкны формат тус бүрээр өгөгдөл авах
                if bank_format == 'khan':
                    description = str(row.get('Гүйлгээний утга', 'Банкны гүйлгээ')).strip()
                    counterparty_name = str(row.get('Харьцсан данс', '')).strip()
                    
                    debit = Decimal(str(row.get('Дебит гүйлгээ', 0))) if pd.notna(row.get('Дебит гүйлгээ')) else Decimal('0')
                    credit = Decimal(str(row.get('Кредит гүйлгээ', 0))) if pd.notna(row.get('Кредит гүйлгээ')) else Decimal('0')
                    
                    # Сөрөг тоог эерэг болгох (Хаан банк сөрөг тоогоор өгдөг)
                    income = abs(credit)
                    expense = abs(debit)
                else:
                    description = str(row.get('Гүйлгээний утга', 'Банкны гүйлгээ')).strip()
                    counterparty_name = str(row.get('Харьцсан дансны нэр', '')).strip()
                    
                    income = Decimal(str(row.get('Орлого', 0))) if pd.notna(row.get('Орлого')) else Decimal('0')
                    expense = Decimal(str(row.get('Зарлага', 0))) if pd.notna(row.get('Зарлага')) else Decimal('0')
                
                # Дүн шалгах
                if income == 0 and expense == 0:
                    skipped_count += 1
                    continue
                
                # Харилцагч үүсгэх
                counterparty = None
                if counterparty_name:
                    counterparty, _ = Counterparty.objects.get_or_create(
                        name=counterparty_name,
                        defaults={'counterparty_type': 'BOTH'}
                    )
                
                # Эцсийн үлдэгдэл (Хаан банк дээр байдаг)
                opening_bal = None
                closing_bal = None
                if bank_format == 'khan':
                    opening_bal = Decimal(str(row.get('Эхний үлдэгдэл', 0))) if pd.notna(row.get('Эхний үлдэгдэл')) else None
                    closing_bal = Decimal(str(row.get('Эцсийн үлдэгдэл', 0))) if pd.notna(row.get('Эцсийн үлдэгдэл')) else None
                
                # Цагийг салгах (datetime-аас)
                transaction_time = transaction_date.time() if isinstance(transaction_date, datetime) else None
                
                # Давхардсан гүйлгээ шалгах (огноо + цаг + данс + дүн + тайлбар)
                # Цагийг мөн шалгаж байгаа нь банкны шимтгэл гэх мэт ижил гүйлгээнүүдийг ялгана
                filter_kwargs = {
                    'bank_account': bank_account,
                    'transaction_date': transaction_date.date(),
                    'description': description,
                    'income_amount': income,
                    'expense_amount': expense
                }
                
                # Хаан банк мөр бүрийн эцсийн үлдэгдэлтэй — энэ нь мөрийг өвөрмөц болгоно.
                # Цагийг тэр үед оруулахгүй: сарын хураамж гэх мэт гүйлгээний цаг хуулга татах
                # бүрт өөр гардаг (жишээ нь 09:54 ба 06:30) тул давхардал үүсгэж байсан.
                if closing_bal is not None:
                    filter_kwargs['closing_balance'] = closing_bal
                # Үлдэгдэлгүй (Голомт) бол цагаар ялгана (нэг өдрийн олон шимтгэл)
                elif transaction_time:
                    filter_kwargs['transaction_time'] = transaction_time

                # Ижил түлхүүртэй хэд дэх мөр вэ гэдгийг тоолно: нэг өдөр ижил утга, ижил дүнтэй
                # хоёр жинхэнэ гүйлгээ (жишээ нь хоёр шимтгэл) байж болно. Файлд N дахь удаа гарч
                # буй мөрийг DB-д ийм түлхүүртэй N-ээс цөөн бичлэг байвал л үүсгэнэ.
                dedup_key = tuple(sorted((k, str(v)) for k, v in filter_kwargs.items() if k != 'bank_account'))
                occurrence = file_occurrences.get(dedup_key, 0)
                file_occurrences[dedup_key] = occurrence + 1
                existing = BankTransaction.objects.filter(**filter_kwargs).count() > occurrence

                if existing:
                    skipped_count += 1
                    if created_count == 0 and skipped_count <= 5:  # Эхний 5 давхардсаныг харуулах
                        time_str = f" {transaction_time}" if transaction_time else ""
                        print(f"  ⊘ Давхардсан: {transaction_date.date()}{time_str} - {description[:40]}...")
                    continue
                
                # 1. БАНКНЫ ГҮЙЛГЭЭ ХАДГАЛАХ (анхны өгөгдөл)
                bank_trans = BankTransaction.objects.create(
                    bank_name='KHAN' if bank_format == 'khan' else 'GOLOMT',
                    bank_account=bank_account,
                    transaction_date=transaction_date.date(),
                    transaction_time=transaction_time,
                    description=description,
                    counterparty_account=str(row.get('Харьцсан данс', '')).strip(),
                    counterparty_name=counterparty_name,
                    counterparty=counterparty,
                    income_amount=income,
                    expense_amount=expense,
                    opening_balance=opening_bal,
                    closing_balance=closing_bal,
                    branch_code=str(row.get('Салбар', '')).strip() if bank_format == 'khan' else '',
                    is_processed=False,  # Эсрэг данс холбоогүй тул боловсруулаагүй
                    offset_account=None  # Ажилтан дараа нь холбоно
                )
                
                # 2. ЖУРНАЛД ОРУУЛАХГҮЙ - Ажилтан эсрэг данс холбоод action дарахад л оруулна
                # accounting_entry үүсгэхгүй
                
                created_count += 1
                if created_count % 10 == 0:
                    print(f"  {created_count} гүйлгээ...")
                
            except Exception as e:
                print(f"✗ Мөр {index + 2}: {str(e)}")
                continue
        
        print(f"\n{'='*60}")
        print(f"✓ Үүссэн гүйлгээ: {created_count}")
        print(f"⊘ Давхардсан (алгассан): {skipped_count}")
        print(f"Дансны эцсийн үлдэгдэл: {bank_account.balance:,.0f}₮")
        print(f"{'='*60}")
        
        return {
            'created': created_count, 
            'skipped': skipped_count,
            'final_balance': bank_account.balance
        }

    except BankImportError:
        raise
    except Exception as e:
        print(f"✗ Алдаа: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def regenerate_accounting_entries(bank_transactions, user):
    """Эсрэг данс холбосон банк/кассын гүйлгээнүүдийг журналд дахин оруулах
    
    Args:
        bank_transactions: BankTransaction QuerySet (банк эсвэл кассын гүйлгээ)
        user: User объект (журналын бичилт үүсгэсэн хэрэглэгч)
    
    Returns:
        int: Шинэчлэгдсэн гүйлгээний тоо
    """
    try:
        from .models import BankTransactionSplit
    except Exception:
        BankTransactionSplit = None
    from decimal import Decimal

    count = 0
    for bt in bank_transactions:
        if bt.transfer_source_id:
            continue  # Автоматаар үүссэн эсрэг мөр — журналыг эх гүйлгээ хариуцна

        if not bt.offset_account:
            continue  # Эсрэг данс холбоогүй бол алгасах

        # Хуучин accounting entry устгах (байвал)
        if bt.accounting_entry:
            old_entry = bt.accounting_entry
            bt.accounting_entry = None
            bt.save(update_fields=['accounting_entry'])
            old_entry.delete()

        # Нэмэлт хуваарилалтуудын хуучин журнал устгах (хэрэв модуль/модель байгаа бол)
        if BankTransactionSplit:
            for split in bt.extra_splits.all():
                if split.accounting_entry:
                    old_split_entry = split.accounting_entry
                    split.accounting_entry = None
                    split.save(update_fields=['accounting_entry'])
                    old_split_entry.delete()
        
        # Шинэ entry үүсгэх
        income = bt.income_amount
        expense = bt.expense_amount

        # Нэмэлт хуваарилалтын нийт дүн тооцоолох (модель байгаа тохиолдолд)
        extra_splits = list(bt.extra_splits.all()) if BankTransactionSplit else []
        extra_total = sum(s.amount for s in extra_splits) if extra_splits else Decimal('0')

        # Үндсэн эсрэг данс руу очих дүн = нийт - нэмэлт хуваарилалт
        if income > 0:
            main_amount = income - extra_total
        else:
            main_amount = expense - extra_total

        from django.db import IntegrityError, transaction

        def _next_seq_and_number(date_key, prefix):
            """Return next sequence-based entry_number for prefix+date_key."""
            return next_entry_number(f'{prefix}{date_key}')

        # Use module-level safe creator to avoid entry_number collisions

        date_key = bt.transaction_date.strftime('%Y%m%d')
        prefix = 'CSH' if bt.account_type == 'CASH' else 'BNK'

        if main_amount > 0:
            if income > 0:
                seq, entry_number = _next_seq_and_number(date_key, prefix)
                entry = create_accounting_entry_safe(
                    entry_date=bt.transaction_date,
                    entry_number=entry_number,
                    description=bt.description,
                    debit_account=bt.bank_account,
                    debit_amount=main_amount,
                    credit_account=bt.offset_account,
                    credit_amount=main_amount,
                    created_by=user
                )
            else:
                seq, entry_number = _next_seq_and_number(date_key, prefix)
                entry = create_accounting_entry_safe(
                    entry_date=bt.transaction_date,
                    entry_number=entry_number,
                    description=bt.description,
                    debit_account=bt.offset_account,
                    debit_amount=main_amount,
                    credit_account=bt.bank_account,
                    credit_amount=main_amount,
                    created_by=user
                )
            bt.accounting_entry = entry

        # Нэмэлт хуваарилалт бүрт тусдаа журналын бичилт үүсгэх
        for split in extra_splits:
            split_desc = split.description or bt.description
            seq, split_entry_number = _next_seq_and_number(date_key, prefix)
            if income > 0:
                split_entry = create_accounting_entry_safe(
                    entry_date=bt.transaction_date,
                    entry_number=split_entry_number,
                    description=split_desc,
                    debit_account=bt.bank_account,
                    debit_amount=split.amount,
                    credit_account=split.account,
                    credit_amount=split.amount,
                    created_by=user
                )
            else:
                split_entry = create_accounting_entry_safe(
                    entry_date=bt.transaction_date,
                    entry_number=split_entry_number,
                    description=split_desc,
                    debit_account=split.account,
                    debit_amount=split.amount,
                    credit_account=bt.bank_account,
                    credit_amount=split.amount,
                    created_by=user
                )
            split.accounting_entry = split_entry
            split.save(update_fields=['accounting_entry'])
        
        bt.is_processed = True
        bt.save(update_fields=['accounting_entry', 'is_processed'])

        # Эсрэг данс касс бол кассын эсрэг мөрийг үүсгэх/шинэчлэх (кассын үлдэгдэл зөв болгох)
        sync_cash_transfer_mirrors(bt, user)

        count += 1

    return count
