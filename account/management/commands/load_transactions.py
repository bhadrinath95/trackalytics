# account/management/commands/load_transactions.py

from django.core.management.base import BaseCommand
from account.models import Transaction, Bank
from account.utils import fetch_google_sheet, preprocess_transaction_data
from datetime import datetime
import os

class Command(BaseCommand):

    def __init__(self):
        self.sheet_id = os.environ.get("SHEET_ID")
        self.sheet_name = os.environ.get("TRANSACTION_SHEET_NAME")

    def handle(self, *args, **kwargs):

        try:
            df = fetch_google_sheet(self.sheet_id, self.sheet_name)
        except ValueError as e:
            print(e)
            return

        Transaction.objects.all().delete()

        df = preprocess_transaction_data(df)

        for _, row in df.iterrows():
            bank_obj, _ = Bank.objects.get_or_create(name=row['Income and Expense Account'])

            Transaction.objects.create(
                account=bank_obj,
                date=datetime.strptime(row['Date'], "%m/%d/%Y"),
                description=row.get('Description', ''),
                category=row.get('Category', ''),
                money_in=row['Income Money IN'],
                money_out=row['Expense Money OUT'],
                account_balance=row['Account Balance']
            )

        print("✅ Transactions imported successfully.")
