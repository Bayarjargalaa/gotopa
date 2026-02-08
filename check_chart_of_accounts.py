#!/usr/bin/env python
"""Дансны төлөвлөгөөний кодуудыг шалгах"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import ChartOfAccounts

print("="*80)
print(f"📋 ДАНСНЫ ТӨЛӨВЛӨГӨӨ")
print("="*80)

# Борлуулалтын орлого хайх
bad_codes = ChartOfAccounts.objects.filter(code='510101')
for acc in bad_codes:
    print(f"\n⚠️ БУРУУ КОД ОЛДЛОО:")
    print(f"  Код: {acc.code}")
    print(f"  Нэр: {acc.name}")
    print(f"  Эхний тэмдэгт: 5 = Зардал")
    print(f"  'Борлуулалтын орлого' нь 4xxx байх ёстой!")
    
# Дансны авлага хайх
bad_codes2 = ChartOfAccounts.objects.filter(code='120101')
for acc in bad_codes2:
    print(f"\n✓ ЗӨВӨӨР БАЙНА:")
    print(f"  Код: {acc.code}")
    print(f"  Нэр: {acc.name}")
    print(f"  Эхний тэмдэгт: 1 = Хөрөнгө")
    print(f"  Дансны авлага = хөрөнгө (зөв)")

# 4xxx орлогын дансууд
print(f"\n💰 ОРЛОГЫН ДАНСУУД (4xxx):")
income_accts = ChartOfAccounts.objects.filter(code__startswith='4', is_active=True).order_by('code')
for acc in income_accts[:10]:
    print(f"  {acc.code} - {acc.name}")

# 5xxx зардлын дансууд
print(f"\n💸 ЗАРДЛЫН ДАНСУУД (5xxx):")
expense_accts = ChartOfAccounts.objects.filter(code__startswith='5', is_active=True).order_by('code')
for acc in expense_accts[:10]:
    print(f"  {acc.code} - {acc.name}")
