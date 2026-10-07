"""Автомат холболтын загвараар (AutoLinkRule) банкны гүйлгээг данс/үзүүлэлттэй холбох.

- find_matches(): холбогдоогүй шинэ үеийн банкны гүйлгээ бүрт эхний таарсан загварыг олно
- apply_link(): эсрэг данс, үзүүлэлт, орлогын төрлийг тохируулж журнал үүсгэнэ
- apply_auto_rules(): "Импортлох үед шууд холбох" загваруудыг шалгалтгүйгээр хэрэглэнэ
"""
from django.db import transaction as db_transaction

from .books_period import period_filter


def candidate_transactions():
    """Загвараар холбож болох гүйлгээнүүд: шинэ үеийн, холбогдоогүй, шилжүүлэг биш банкны гүйлгээ."""
    from .models import BankTransaction
    qs = BankTransaction.objects.filter(
        account_type='BANK',
        is_processed=False,
        accounting_entry__isnull=True,
        transfer_source__isnull=True,
        transfer_link_as_income__isnull=True,
        transfer_link_as_expense__isnull=True,
    ).select_related('bank_account')
    return period_filter(qs, 'transaction_date').order_by('-transaction_date', '-id')


def active_rules(auto_only=False):
    from .models import AutoLinkRule
    rules = AutoLinkRule.objects.filter(is_active=True).select_related('offset_account', 'cash_flow_indicator')
    if auto_only:
        rules = rules.filter(auto_apply=True)
    return list(rules.order_by('priority', 'id'))


def find_matches(rules=None, transactions=None):
    """[(tx, rule)] — гүйлгээ бүрт эрэмбээр эхэлж таарсан загвар."""
    rules = active_rules() if rules is None else rules
    if not rules:
        return []
    transactions = candidate_transactions() if transactions is None else transactions
    matches = []
    for tx in transactions:
        for rule in rules:
            if rule.matches(tx):
                matches.append((tx, rule))
                break
    return matches


def apply_link(tx, offset_account, indicator_id, income_type, user):
    """Гүйлгээнд эсрэг данс тохируулж журнал үүсгэнэ."""
    from .import_bank_transactions import regenerate_accounting_entries
    tx.offset_account = offset_account
    tx.cash_flow_indicator_id = indicator_id or None
    if tx.income_amount > 0 and income_type:
        tx.income_type = income_type
    tx.save(update_fields=['offset_account', 'cash_flow_indicator', 'income_type'])
    regenerate_accounting_entries([tx], user)


def apply_auto_rules(user, bank_account=None):
    """"Импортлох үед шууд холбох" загваруудыг хэрэглээд холбосон тоог буцаана."""
    rules = active_rules(auto_only=True)
    if not rules:
        return 0
    transactions = candidate_transactions()
    if bank_account is not None:
        transactions = transactions.filter(bank_account=bank_account)
    count = 0
    with db_transaction.atomic():
        for tx, rule in find_matches(rules, transactions):
            apply_link(tx, rule.offset_account, rule.cash_flow_indicator_id, rule.income_type, user)
            count += 1
    return count
