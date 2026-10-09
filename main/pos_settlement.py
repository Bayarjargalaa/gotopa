"""POS картын сэттлмэнтийг таних туслахууд.

ХАС банкны хуулгад POS-ын өдрийн тооцоо хоёр мөрөөр ирдэг:
    "2026.09.28, 187, 44311091 СЕТТЛЕМЕНТ ХААВ"                 +20,000  (өдрийн нийт борлуулалт)
    "2026.09.28, 187, 44311091 СЕТТЛЕМЕНТИЙН ШИМТГЭЛ СУУТГАВ"   −200     (1% шимтгэл)
Утган дахь огноо = борлуулалт хийсэн өдөр (хуулгад дараа өдөр нь орно).

Сэттлмэнтийг борлуулалтуудтай холбохдоо (борлуулалтын дэлгэрэнгүй эсвэл банкны гүйлгээний
"Олон борлуулалттай холбох" хэсгээс) SalePaymentAllocation үүсч, орлогын журнал
(Дт банк / Кт 510101) sync_sale_revenue_journal-аар бичигдэнэ. Шимтгэлийн мөрийг
"Автомат холболтын загвар" (702701) хариуцна.
"""
import re
from datetime import date

SETTLEMENT_MARK = 'СЕТТЛЕМЕНТ ХААВ'
_DATE_RE = re.compile(r'(\d{4})\.(\d{2})\.(\d{2})')


def is_settlement(tx):
    return SETTLEMENT_MARK in (tx.description or '') and (tx.income_amount or 0) > 0


def business_date(description):
    """Утгаас борлуулалт хийсэн өдрийг ('2026.09.28') гаргана."""
    m = _DATE_RE.search(description or '')
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def settlement_date(tx):
    """Сэттлмэнт бол аль өдрийн борлуулалтынх болохыг, үгүй бол None буцаана."""
    if not is_settlement(tx):
        return None
    return business_date(tx.description) or tx.transaction_date
