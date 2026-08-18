from main.models import IncomeCategory, BankTransaction

created = []
for code, name in BankTransaction.INCOME_TYPE_CHOICES:
    obj, is_new = IncomeCategory.objects.get_or_create(code=code, defaults={'name': name})
    if is_new:
        created.append(code)

print('Created IncomeCategory codes:', created)
print('Total IncomeCategory count:', IncomeCategory.objects.count())
