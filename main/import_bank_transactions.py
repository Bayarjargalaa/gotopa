"""
Банкны хуулгын файлаас гүйлгээг импортлох (Хаан болон Голомт банк)

Дэмжигдсэн форматууд:

1. Хаан банк:
   Гүйлгээний огноо | Салбар | Эхний үлдэгдэл | Дебит гүйлгээ | Кредит гүйлгээ | Эцсийн үлдэгдэл | Гүйлгээний утга | Харьцсан данс

2. Голомт банк:
   Гүйлгээний огноо | Гүйлгээний утга | Харьцсан дансны нэр | Харьцсан данс | Ханш | Орлого | Зарлага
"""

import pandas as pd
from main.models import BankTransaction, AccountingEntry, ChartOfAccounts, Counterparty
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from django.db import IntegrityError, transaction


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
                prefix = m.group('prefix')
                date_key = m.group('date')
                existing = AccountingEntry.objects.filter(entry_number__startswith=f'{prefix}{date_key}').count()
                kwargs['entry_number'] = f"{prefix}{date_key}{existing + 1:04d}"
                continue
            suffix = uuid.uuid4().hex[:6].upper()
            kwargs['entry_number'] = f"{en}-{suffix}"
            continue
    # If we exit loop without returning, re-raise the last caught exception
    if last_exc:
        raise last_exc
    raise IntegrityError('Failed to create AccountingEntry after retries')


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


def detect_bank_format(df):
    """Банкны хуулгын форматыг баганын нэрээс таних"""
    columns = [col.strip() for col in df.columns]
    
    if 'Дебит гүйлгээ' in columns and 'Кредит гүйлгээ' in columns:
        return 'khan'
    
    if 'Орлого' in columns and 'Зарлага' in columns:
        return 'golomt'
    
    return None


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
        df_preview = pd.read_excel(excel_file, engine='openpyxl', header=None, nrows=10)
        
        # "Гүйлгээний огноо" гэсэн баганыг хайх (header мөр)
        header_row = None
        for idx, row in df_preview.iterrows():
            if any('Гүйлгээний огноо' in str(cell) for cell in row):
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
        
        print(f"✓ Банк: {'Хаан банк' if bank_format == 'khan' else 'Голомт банк'}\n")
        
        created_count = 0
        skipped_count = 0
        
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
                
                # Цаг байвал цагаар нь шалгах (банкны шимтгэл гэх мэт давхардах магадлалтай)
                if transaction_time:
                    filter_kwargs['transaction_time'] = transaction_time
                
                existing = BankTransaction.objects.filter(**filter_kwargs).first()
                
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
            existing = AccountingEntry.objects.filter(
                entry_number__startswith=f'{prefix}{date_key}'
            ).count()
            return existing + 1, f"{prefix}{date_key}{existing + 1:04d}"

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
