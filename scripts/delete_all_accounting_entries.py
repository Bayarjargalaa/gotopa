#!/usr/bin/env python
import os
import django
import sys
import time

# Ensure project root is on sys.path so Django settings module can be imported
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gotopa_project.settings')
django.setup()

from main.models import AccountingEntry, BankTransaction
from django.db import transaction


def main():
    total = AccountingEntry.objects.count()
    print(f"Found {total} AccountingEntry objects.")
    if total == 0:
        print("Nothing to delete.")
        return

    # Proceeding because user explicitly requested destructive action.
    deleted = 0
    start = time.time()
    for ae in AccountingEntry.objects.select_related('debit_account', 'credit_account').all():
        try:
            with transaction.atomic():
                ae_id = ae.id
                ae_number = ae.entry_number
                ae.delete()
            deleted += 1
            if deleted % 100 == 0:
                print(f"Deleted {deleted}/{total}...")
        except Exception as e:
            print(f"Error deleting entry id={ae_id} number={ae_number}: {e}", file=sys.stderr)

    duration = time.time() - start
    print(f"Deleted {deleted} entries in {duration:.1f}s")

    remaining = AccountingEntry.objects.count()
    print(f"Remaining AccountingEntry: {remaining}")
    linked = BankTransaction.objects.filter(accounting_entry__isnull=False).count()
    print(f"BankTransaction still linked: {linked}")


if __name__ == '__main__':
    main()
