"""Банкны гүйлгээг холбох хуудсанд зориулсан автомат санал болголтууд.

- Гүйлгээний утга / харилцагчийн данснаас сурагчийг таах
- Утгаас төлбөрийн сарыг таах
- Орлогын төрөл бүрийн анхдагч эсрэг данс, мөнгөн гүйлгээний үзүүлэлт
- Эсрэг данс бүрт хамгийн их ашиглагдсан үзүүлэлт
- Ижил харилцагчийн өмнөх гүйлгээ хэрхэн холбогдсон
- Хуулга хүлээж буй (урьдчилан тэмдэглэсэн) төлбөрүүдээс тохирохыг олох
"""
import re
from collections import Counter, defaultdict
from datetime import timedelta

from django.db.models import Count, Q

from .models import BankTransaction, ChartOfAccounts, CashFlowIndicator, PaymentAllocation, PendingPayment


# Орлогын төрлийн тогтмол анхдагч утгууд (дансны код, үзүүлэлтийн код).
# Бусад төрлийн анхдагчийг өмнөх гүйлгээнүүдээс тооцоолно.
FIXED_TYPE_DEFAULTS = {
    'STUDENT_PAYMENT': ('510102', '1.1.1'),
    'PRODUCT_SALE': ('510101', '1.1.1'),
    'DONATION': ('840502', '3.1.3'),
}

_CYR_TO_LAT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'io', 'ж': 'j',
    'з': 'z', 'и': 'i', 'й': 'i', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'ө': 'u', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ү': 'u', 'ф': 'f',
    'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh', 'ъ': 'i', 'ы': 'i', 'ь': 'i',
    'э': 'e', 'ю': 'iu', 'я': 'ia',
}


_EMPTY_VALUES = {'', 'nan', 'none', 'null', '-'}


def clean_text(value):
    """Excel импортоос ирсэн 'nan' зэрэг хоосон утгыг '' болгоно."""
    value = (value or '').strip()
    return '' if value.lower() in _EMPTY_VALUES else value


def normalize_account(value):
    """'5021172243.0' гэх мэт Excel-ийн үлдэгдлийг цэвэрлэнэ."""
    value = clean_text(value).replace(' ', '')
    if value.endswith('.0'):
        value = value[:-2]
    return value


def _account_variants(value):
    acc = normalize_account(value)
    return [acc, f'{acc}.0'] if acc else []


def _name_key(text):
    """Кирилл болон латин бичлэгийг нэг хэлбэрт оруулж харьцуулах түлхүүр.

    Жишээ: 'Аззаяа' болон 'AZZAYA' хоёулаа 'azaia' болно.
    """
    text = (text or '').lower()
    text = ''.join(_CYR_TO_LAT.get(ch, ch) for ch in text)
    text = re.sub(r'[^a-z]', '', text)
    for src, dst in (('kh', 'h'), ('ts', 'c'), ('tz', 'c'), ('w', 'v'), ('q', 'k'), ('y', 'i'), ('x', 'h')):
        text = text.replace(src, dst)
    # Давхардсан үсгийг нэг болгох (azzaya -> azaia, ulzii -> ulzi)
    return re.sub(r'(.)\1+', r'\1', text)


def _description_name_keys(tx):
    """Утга + харилцагчийн нэрээс үгсийн түлхүүрүүд (зэргэлдээ хоёр үгийн нийлбэр мөн)."""
    text = f'{tx.description or ""} {clean_text(tx.counterparty_name)}'
    words = [w for w in re.split(r'[^0-9A-Za-zА-Яа-яӨөҮүЁё]+', text) if w]
    keys = {_name_key(w) for w in words}
    # 'BAYAN ZUL' -> 'bayanzul'
    keys |= {_name_key(a + b) for a, b in zip(words, words[1:])}
    return {k for k in keys if len(k) >= 4}


def suggest_students(tx, students, limit=3):
    """Гүйлгээнд тохирох сурагчдыг оноогоор эрэмбэлж буцаана.

    Returns: [{'id', 'reasons': [...], 'score', 'strong'}]
    """
    scores = defaultdict(int)
    reasons = defaultdict(list)

    def add(student_id, points, reason):
        scores[student_id] += points
        if reason not in reasons[student_id]:
            reasons[student_id].append(reason)

    # 1) Өмнө нь энэ данснаас төлбөр хийсэн сурагчид
    variants = _account_variants(tx.counterparty_account)
    if variants:
        history = Counter(
            PaymentAllocation.objects
            .filter(transaction__counterparty_account__in=variants)
            .exclude(transaction=tx)
            .values_list('student_id', flat=True)
        )
        for student_id, count in history.items():
            add(student_id, 5 + min(count, 3), 'Өмнө энэ данснаас төлсөн')

    # 2) Утганд сурагчийн утасны дугаар байгаа
    phones = set(re.findall(r'(?<!\d)\d{8}(?!\d)', tx.description or ''))
    name_keys = _description_name_keys(tx)

    # Овгийн эхний үсэг: 'Х. МӨНХБАЯР' гэх мэт ганц үсэг, эсвэл харилцагчийн
    # нэрийн эхний үг (банк 'ОВОГ НЭР' хэлбэрээр өгдөг)
    words = [w for w in re.split(r'[^A-Za-zА-Яа-яӨөҮүЁё]+', tx.description or '') if w]
    initials = {w.lower() for w in words if len(w) == 1}
    counterparty_words = clean_text(tx.counterparty_name).split()
    if counterparty_words:
        initials.add(counterparty_words[0][0].lower())

    for student in students:
        if student.phone and student.phone.strip() in phones:
            add(student.id, 6, 'Утасны дугаар таарсан')

        # 3) Нэр (кирилл/латин) таарсан
        first_key = _name_key(student.first_name)
        if len(first_key) >= 4 and first_key in name_keys:
            last_key = _name_key(student.last_name)
            last_name = (student.last_name or '').strip().rstrip('.')
            if len(last_key) >= 4 and last_key in name_keys:
                add(student.id, 3, 'Нэр, овог таарсан')
            elif last_name and len(last_name) <= 2 and last_name[0].lower() in initials:
                add(student.id, 3, 'Нэр, овгийн үсэг таарсан')
            else:
                add(student.id, 2, 'Нэр таарсан')

    ranked = sorted(scores.items(), key=lambda item: -item[1])[:limit]
    result = []
    for index, (student_id, score) in enumerate(ranked):
        next_score = ranked[index + 1][1] if index + 1 < len(ranked) else 0
        result.append({
            'id': student_id,
            'score': score,
            'reasons': reasons[student_id],
            # Итгэлтэй санал: утас/данс таарсан эсвэл дараагийнхаасаа тодорхой илүү
            'strong': index == 0 and (score >= 5 or (score >= 2 and score > next_score)),
        })
    return result


def suggest_pending_payments(tx, student_suggestions, limit=6):
    """Гүйлгээнд тохирох, банкны гүйлгээтэй холбогдоогүй урьдчилсан тэмдэглэлүүд.

    Огноо ойр (−10..+3 хоног) эсвэл санал болгосон сурагчийн тэмдэглэлүүдийг
    дүн, сурагч, төлөгчийн нэр, огноогоор оноолно.
    Returns: [{'pending': PendingPayment, 'reasons': [...], 'score', 'strong'}]
    """
    amount = tx.income_amount or 0
    if amount <= 0:
        return []
    tx_date = tx.transaction_date
    suggested_ids = {s['id'] for s in student_suggestions}

    candidates = (
        PendingPayment.objects
        .filter(allocation__isnull=True, pre_start=False, amount__lte=amount)
        .filter(
            Q(paid_date__gte=tx_date - timedelta(days=10), paid_date__lte=tx_date + timedelta(days=3))
            | Q(student_id__in=suggested_ids, paid_date__gte=tx_date - timedelta(days=60))
        )
        .select_related('student', 'course')
    )
    name_keys = _description_name_keys(tx)

    scored = []
    for pending in candidates:
        score, reasons = 0, []
        if pending.amount == amount:
            score += 5
            reasons.append('Дүн таарсан')
        if pending.student_id in suggested_ids:
            score += 4
            reasons.append('Сурагч таарсан')
        payer_keys = {_name_key(w) for w in re.split(r'[^0-9A-Za-zА-Яа-яӨөҮүЁё]+', pending.payer_name) if w}
        if payer_keys & name_keys:
            score += 4
            reasons.append('Төлөгчийн нэр таарсан')
        days = abs((tx_date - pending.paid_date).days)
        if days <= 1:
            score += 2
            reasons.append('Огноо таарсан')
        elif days <= 3:
            score += 1
        scored.append({'pending': pending, 'reasons': reasons, 'score': score})

    scored.sort(key=lambda item: (-item['score'], item['pending'].paid_date))
    scored = scored[:limit]
    # Итгэлтэй: дүн таарч, сурагч/нэр/огноо ч таарсан, бусдаасаа тодорхой илүү
    for index, item in enumerate(scored):
        next_score = scored[index + 1]['score'] if index + 1 < len(scored) else 0
        item['strong'] = index == 0 and item['score'] >= 7 and item['score'] > next_score
    return scored


_MONTH_RE = re.compile(
    r'(?<!\d)(1[0-2]|0?[1-9])\s*[-–.]?\s*(?:р|r|n|н|дугаар|dugaar|дахь|dahi|dh)?\s*(?:сар|sar)',
    re.IGNORECASE,
)


def suggest_month(tx):
    """Утгаас ('4-р сар', '6-R SAR') сарыг олох, олдохгүй бол гүйлгээний сар. 'YYYY-MM' буцаана."""
    tx_date = tx.transaction_date
    year, month = tx_date.year, tx_date.month
    match = _MONTH_RE.search(tx.description or '')
    if match:
        found = int(match.group(1))
        # Өмнөх/дараагийн оны сар байж болно (12-р сард 1-р сарын төлбөр гэх мэт)
        if found - month > 6:
            year -= 1
        elif month - found > 6:
            year += 1
        month = found
    return f'{year:04d}-{month:02d}'


def _most_common_pairs(queryset, key_field):
    """key_field бүрт хамгийн их давтагдсан (offset_account_id, cash_flow_indicator_id)."""
    rows = (
        queryset
        .values(key_field, 'offset_account_id', 'cash_flow_indicator_id')
        .annotate(n=Count('id'))
        .order_by(key_field, '-n')
    )
    result = {}
    for row in rows:
        key = row[key_field]
        if key is None or key in result:
            continue
        result[key] = (row['offset_account_id'], row['cash_flow_indicator_id'])
    return result


def type_defaults():
    """{income_type: {'account': id, 'indicator': id}} — анхдагч данс, үзүүлэлт."""
    processed = BankTransaction.objects.filter(
        is_processed=True, income_amount__gt=0, offset_account__isnull=False
    )
    defaults = {}
    for income_type, (account_id, indicator_id) in _most_common_pairs(processed, 'income_type').items():
        defaults[income_type] = {'account': account_id, 'indicator': indicator_id}

    account_ids = dict(ChartOfAccounts.objects.filter(
        code__in=[a for a, _ in FIXED_TYPE_DEFAULTS.values()]
    ).values_list('code', 'id'))
    indicator_ids = dict(CashFlowIndicator.objects.filter(
        code__in=[i for _, i in FIXED_TYPE_DEFAULTS.values()]
    ).values_list('code', 'id'))
    for income_type, (account_code, indicator_code) in FIXED_TYPE_DEFAULTS.items():
        defaults[income_type] = {
            'account': account_ids.get(account_code),
            'indicator': indicator_ids.get(indicator_code),
        }
    return defaults


def account_indicator_map(is_income):
    """{offset_account_id: cash_flow_indicator_id} — тухайн дансанд хамгийн их хэрэглэгдсэн үзүүлэлт."""
    processed = BankTransaction.objects.filter(
        is_processed=True, cash_flow_indicator__isnull=False, offset_account__isnull=False
    )
    processed = processed.filter(income_amount__gt=0) if is_income else processed.filter(expense_amount__gt=0)
    rows = (
        processed.values('offset_account_id', 'cash_flow_indicator_id')
        .annotate(n=Count('id'))
        .order_by('offset_account_id', '-n')
    )
    result = {}
    for row in rows:
        result.setdefault(row['offset_account_id'], row['cash_flow_indicator_id'])
    return result


def counterparty_history(tx):
    """Ижил харилцагчийн хамгийн сүүлд холбогдсон гүйлгээ (ижил чиглэлтэй)."""
    base = BankTransaction.objects.filter(
        is_processed=True, offset_account__isnull=False
    ).exclude(id=tx.id).select_related('offset_account', 'cash_flow_indicator')
    base = base.filter(income_amount__gt=0) if tx.income_amount > 0 else base.filter(expense_amount__gt=0)

    previous = None
    variants = _account_variants(tx.counterparty_account)
    if variants:
        previous = base.filter(counterparty_account__in=variants).order_by('-transaction_date', '-id').first()
    counterparty_name = clean_text(tx.counterparty_name)
    if not previous and counterparty_name:
        previous = base.filter(counterparty_name=counterparty_name).order_by('-transaction_date', '-id').first()
    if not previous:
        return None

    return {
        'id': previous.id,
        'date': previous.transaction_date,
        'description': previous.description,
        'income_type': previous.income_type or '',
        'account_id': previous.offset_account_id,
        'account_label': f'{previous.offset_account.code} - {previous.offset_account.name}',
        'indicator_id': previous.cash_flow_indicator_id,
        'indicator_code': previous.cash_flow_indicator.code if previous.cash_flow_indicator else '',
    }
