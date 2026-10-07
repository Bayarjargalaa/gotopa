"""POS картын борлуулалтыг банкны сэттлмэнттэй тулгах.

ХАС банкны хуулгад POS-ын өдрийн тооцоо хоёр мөрөөр ирдэг:
    "2026.09.28, 187, 44311091 СЕТТЛЕМЕНТ ХААВ"                 +20,000  (өдрийн нийт борлуулалт)
    "2026.09.28, 187, 44311091 СЕТТЛЕМЕНТИЙН ШИМТГЭЛ СУУТГАВ"   −200     (1% шимтгэл)
Утган дахь огноо = борлуулалт хийсэн өдөр (хуулгад дараа өдөр нь орно).

Холбоход:
  - сэттлмэнт ↔ тухайн өдрийн POS борлуулалтууд (SalePaymentAllocation),
    журнал: Дт <банк> / Кт 510101 Борлуулалтын орлого
  - шимтгэлийн мөр: Дт 702701 Банкны шимтгэлийн зардал / Кт <банк>, үзүүлэлт 1.2.9
"""
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models import Q, Sum

from .books_period import period_filter

SETTLEMENT_MARK = 'СЕТТЛЕМЕНТ ХААВ'
FEE_MARK = 'СЕТТЛЕМЕНТИЙН ШИМТГЭЛ'
_DATE_RE = re.compile(r'(\d{4})\.(\d{2})\.(\d{2})')
_TERMINAL_RE = re.compile(r'\d{4}\.\d{2}\.\d{2},\s*\d+,\s*(\d+)')

REVENUE_ACCOUNT_CODE = '510101'
FEE_ACCOUNT_CODE = '702701'
REVENUE_INDICATOR_CODE = '1.1.1'
FEE_INDICATOR_CODE = '1.2.9'
DEFAULT_POS_BANK_CODE = '110103'  # ХАС банк


def business_date(description):
    """Утгаас борлуулалт хийсэн өдрийг ('2026.09.28') гаргана."""
    m = _DATE_RE.search(description or '')
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def terminal_id(description):
    m = _TERMINAL_RE.search(description or '')
    return m.group(1) if m else ''


def default_pos_bank():
    from .models import ChartOfAccounts
    return ChartOfAccounts.objects.filter(code=DEFAULT_POS_BANK_CODE).first()


@dataclass
class SettlementRow:
    settlement: object                 # BankTransaction (СЕТТЛЕМЕНТ ХААВ)
    business_date: date
    terminal: str
    fee_tx: object = None              # BankTransaction (шимтгэл) эсвэл None
    sales: list = field(default_factory=list)   # холбогдоогүй POS борлуулалт
    linked_sales: list = field(default_factory=list)

    @property
    def amount(self):
        return self.settlement.income_amount

    @property
    def fee(self):
        return self.fee_tx.expense_amount if self.fee_tx else Decimal('0')

    @property
    def sales_total(self):
        return sum((s.total_amount for s in self.sales), Decimal('0'))

    @property
    def difference(self):
        return self.sales_total - self.amount

    @property
    def is_linked(self):
        return bool(self.settlement.accounting_entry_id)

    @property
    def is_matched(self):
        return not self.is_linked and self.sales and self.difference == 0


def _unlinked_pos_sales(bank_account, sale_date):
    from .models import Sale
    return list(
        Sale.objects.filter(pos_bank_account=bank_account, sale_date=sale_date)
        .exclude(status='CANCELLED')
        .exclude(payment_allocations__isnull=False)
        .select_related('customer')
        .order_by('id')
    )


def settlement_queryset():
    from .models import BankTransaction
    return period_filter(
        BankTransaction.objects.filter(account_type='BANK', description__contains=SETTLEMENT_MARK),
        'transaction_date',
    ).select_related('bank_account', 'accounting_entry')


def _fee_for(settlement, bdate):
    from .models import BankTransaction
    candidates = BankTransaction.objects.filter(
        bank_account=settlement.bank_account,
        description__contains=FEE_MARK,
        expense_amount__gt=0,
        transaction_date__gte=settlement.transaction_date,
    ).order_by('transaction_date', 'id')
    for fee in candidates[:10]:
        if business_date(fee.description) == bdate and terminal_id(fee.description) == terminal_id(settlement.description):
            return fee
    return None


def build_rows():
    """Шинэ үеийн бүх сэттлмэнтийг тухайн өдрийн POS борлуулалттай тулгасан мөрүүд."""
    rows = []
    for st in settlement_queryset().order_by('-transaction_date', '-id'):
        bdate = business_date(st.description) or st.transaction_date
        row = SettlementRow(settlement=st, business_date=bdate, terminal=terminal_id(st.description))
        row.fee_tx = _fee_for(st, bdate)
        if row.is_linked:
            row.linked_sales = [a.sale for a in st.sale_allocations.select_related('sale__customer')]
        else:
            row.sales = _unlinked_pos_sales(st.bank_account, bdate)
        rows.append(row)
    return rows


def pending_pos_sales(rows=None):
    """Сэттлмэнт нь хуулгад хараахан ороогүй (холбогдоогүй) POS борлуулалтууд.

    Сэттлмэнт нь ирсэн (зөрүүтэй ч гэсэн) өдрийн борлуулалт дээрх хүснэгтэд харагдах тул энд оруулахгүй.
    """
    from .models import Sale
    rows = build_rows() if rows is None else rows
    settled = {(r.settlement.bank_account_id, r.business_date) for r in rows}
    sales = (
        period_filter(Sale.objects.filter(pos_bank_account__isnull=False), 'sale_date')
        .exclude(status='CANCELLED')
        .exclude(payment_allocations__isnull=False)
        .select_related('customer', 'pos_bank_account')
        .order_by('-sale_date', '-id')
    )
    return [s for s in sales if (s.pos_bank_account_id, s.sale_date) not in settled]


def ready_count():
    return sum(1 for r in build_rows() if r.is_matched)


def _accounts():
    from .models import ChartOfAccounts, CashFlowIndicator
    revenue = ChartOfAccounts.objects.filter(code=REVENUE_ACCOUNT_CODE).first()
    fee = ChartOfAccounts.objects.filter(code=FEE_ACCOUNT_CODE).first()
    if not revenue or not fee:
        raise ValueError(f'{REVENUE_ACCOUNT_CODE} эсвэл {FEE_ACCOUNT_CODE} данс олдсонгүй.')
    indicators = dict(CashFlowIndicator.objects.filter(
        code__in=[REVENUE_INDICATOR_CODE, FEE_INDICATOR_CODE]).values_list('code', 'id'))
    return revenue, fee, indicators.get(REVENUE_INDICATOR_CODE), indicators.get(FEE_INDICATOR_CODE)


def _create_entry(tx, debit, credit, amount, description, user):
    from .import_bank_transactions import create_accounting_entry_safe, next_entry_number
    _, number = next_entry_number(f"BNK{tx.transaction_date:%Y%m%d}")
    return create_accounting_entry_safe(
        entry_date=tx.transaction_date, entry_number=number, description=description,
        debit_account=debit, debit_amount=amount, credit_account=credit, credit_amount=amount,
        created_by=user,
    )


def _recalc_sale(sale):
    from .models import SalePaymentAllocation
    paid = SalePaymentAllocation.objects.filter(sale=sale).aggregate(s=Sum('amount'))['s'] or Decimal('0')
    sale.paid_amount = paid
    if paid >= sale.total_amount and sale.status == 'DRAFT':
        sale.status = 'PAID'
    elif paid < sale.total_amount and sale.status == 'PAID':
        sale.status = 'DRAFT'
    sale.save(update_fields=['paid_amount', 'status'])


def link_settlement(row, user):
    """Тэнцсэн сэттлмэнтийг борлуулалт, журнал, шимтгэлтэй холбоно."""
    from .models import SalePaymentAllocation
    if row.is_linked:
        raise ValueError('Энэ сэттлмэнт аль хэдийн холбогдсон.')
    if not row.sales:
        raise ValueError(f'{row.business_date:%Y-%m-%d}-ны POS борлуулалт олдсонгүй.')
    if row.difference != 0:
        raise ValueError(f'Дүн тэнцэхгүй (зөрүү {row.difference:,.0f}₮).')

    revenue, fee_account, revenue_ind, fee_ind = _accounts()
    st = row.settlement
    bank = st.bank_account
    with db_transaction.atomic():
        for sale in row.sales:
            SalePaymentAllocation.objects.create(transaction=st, sale=sale, amount=sale.total_amount)
            if not sale.payment_date:
                sale.payment_date = st.transaction_date
                sale.save(update_fields=['payment_date'])
            _recalc_sale(sale)

        sale_numbers = ', '.join(s.sale_number or str(s.id) for s in row.sales)
        entry = _create_entry(st, bank, revenue, st.income_amount,
                              f'POS сэттлмэнт {row.business_date:%Y-%m-%d} ({sale_numbers})', user)
        st.accounting_entry = entry
        st.offset_account = revenue
        st.income_type = 'PRODUCT_SALE'
        st.cash_flow_indicator_id = revenue_ind
        st.is_processed = True
        st.save()

        fee_tx = row.fee_tx
        if fee_tx and not fee_tx.accounting_entry_id:
            fee_entry = _create_entry(fee_tx, fee_account, bank, fee_tx.expense_amount,
                                      f'POS сэттлмэнтийн шимтгэл {row.business_date:%Y-%m-%d}', user)
            fee_tx.accounting_entry = fee_entry
            fee_tx.offset_account = fee_account
            fee_tx.cash_flow_indicator_id = fee_ind
            fee_tx.is_processed = True
            fee_tx.save()


def unlink_settlement(row):
    """Сэттлмэнт болон шимтгэлийн холболтыг цуцлана (борлуулалт дахин "холбогдоогүй" болно)."""
    st = row.settlement
    with db_transaction.atomic():
        sales = [a.sale for a in st.sale_allocations.select_related('sale')]
        st.sale_allocations.all().delete()
        for sale in sales:
            _recalc_sale(sale)
        for tx in [st, row.fee_tx]:
            if not tx or not tx.accounting_entry_id:
                continue
            entry = tx.accounting_entry
            tx.accounting_entry = None
            tx.offset_account = None
            tx.cash_flow_indicator = None
            tx.is_processed = False
            if tx is st:
                tx.income_type = None
            tx.save()
            entry.delete()
