"""Давхцсан хуулгыг дахин импортлосноор давхардсан банкны гүйлгээг илрүүлж цэвэрлэх.

Давхардлын түлхүүр нь импортын давхардал шалгалттай ижил:
  - Хас банк: (данс, огноо, гүйлгээний дугаар, орлого, зарлага)
  - Хаан банк (мөр бүр үлдэгдэлтэй): (данс, огноо, утга, орлого, зарлага, үлдэгдэл)
  - Голомт (цагтай, үлдэгдэлгүй): импорт цагаар зөв ялгадаг тул хамаарахгүй
Нэг хуулгад ижил түлхүүртэй хэд хэдэн жинхэнэ мөр байж болно (жишээ нь ижил шимтгэл),
тиймээс нэг импортод (импортолсон минут) хамгийн олон гарсан тоог жинхэнэ гэж үзээд
илүүг нь давхардал гэж тооцно.
"""
from collections import Counter, defaultdict

from django.db import transaction as db_transaction


def _key(tx):
    if tx.bank_name == 'XAC':
        return ('XAC', tx.bank_account_id, tx.transaction_date, tx.reference_number,
                tx.income_amount, tx.expense_amount)
    if tx.bank_name == 'KHAN' and tx.closing_balance is not None:
        return ('KHAN', tx.bank_account_id, tx.transaction_date, tx.description,
                tx.income_amount, tx.expense_amount, tx.closing_balance)
    return None


def _import_batch(tx):
    return tx.imported_at.replace(second=0, microsecond=0) if tx.imported_at else None


def blockers(tx):
    """Автоматаар устгахад саад болох холболтууд (журналаас бусад)."""
    reasons = []
    if tx.allocations.exists():
        reasons.append('сурагчийн төлбөр')
    if tx.sale_allocations.exists() or tx.income_sale_id:
        reasons.append('борлуулалт')
    if tx.transfer_mirrors.exists():
        reasons.append('кассын эсрэг мөр')
    if tx.transfer_link:
        reasons.append('харилцах хоорондын шилжүүлэг')
    if hasattr(tx, 'extra_splits') and tx.extra_splits.exists():
        reasons.append('нэмэлт хуваарилалт')
    if tx.accounting_entry_id:
        from .models import BankTransaction
        if BankTransaction.objects.filter(accounting_entry_id=tx.accounting_entry_id).exclude(id=tx.id).exists():
            reasons.append('өөр гүйлгээтэй хуваалцсан журнал')
    return reasons


def _is_linked(tx):
    return bool(tx.accounting_entry_id or blockers(tx))


def find_duplicates(queryset=None):
    """[{'keep': [tx...], 'remove': [tx...]}] — холболттой нь, дараа нь эртний нь үлдэнэ."""
    from .models import BankTransaction
    qs = queryset if queryset is not None else BankTransaction.objects.filter(account_type='BANK')
    groups = defaultdict(list)
    for tx in qs.select_related('bank_account', 'accounting_entry').order_by('id'):
        key = _key(tx)
        if key:
            groups[key].append(tx)

    result = []
    for txs in groups.values():
        if len(txs) < 2:
            continue
        genuine = max(Counter(_import_batch(t) for t in txs).values())
        if len(txs) <= genuine:
            continue
        ranked = sorted(txs, key=lambda t: (not _is_linked(t), t.id))
        result.append({'keep': ranked[:genuine], 'remove': ranked[genuine:]})
    result.sort(key=lambda g: (g['keep'][0].bank_account_id, g['keep'][0].transaction_date))
    return result


def remove_duplicate(tx):
    """Давхардсан гүйлгээг (өөрийн журналын хамт) устгана. Саад байвал устгахгүй, шалтгааныг буцаана."""
    reasons = blockers(tx)
    if reasons:
        return reasons
    with db_transaction.atomic():
        entry = tx.accounting_entry
        if entry:
            tx.accounting_entry = None
            tx.save(update_fields=['accounting_entry'])
            entry.delete()  # дансны үлдэгдлийг буцаана
        tx.delete()
    return []
