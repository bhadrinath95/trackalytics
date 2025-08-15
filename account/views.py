from django.shortcuts import render
from .models import Transaction, Bank
from .forms import DateRangeForm, CategoryForm, CategoryTrendForm
from collections import defaultdict, OrderedDict
import random
import json
import locale
from .utils import fetch_google_sheet, preprocess_transaction_data
from datetime import datetime
import os
from django.db.models import Sum
import pandas as pd
from django.db.models.functions import TruncMonth, TruncYear

# Set Indian currency formatting
locale.setlocale(locale.LC_ALL, 'en_IN.UTF-8')

def format_inr(amount):
    return f"₹{locale.format_string('%.2f', amount, grouping=True)}"

def get_random_colors(n):
    return [f'#{random.randint(0, 0xFFFFFF):06x}' for _ in range(n)]

# Home view
def home_view(request):
    context = {
        "message": None,
        "success": None
    }
    
    if request.method == "POST":
        sheet_id = os.environ.get("SHEET_ID")
        sheet_name = os.environ.get("TRANSACTION_SHEET_NAME")
        try:
            df = fetch_google_sheet(sheet_id, sheet_name)
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
            context = {
                "message": "✅ Transactions imported successfully.",
                "success": True
            }
        except Exception as e:
            context = {
                "message": str(e),
                "success": False
            }

        return render(request, "account/partials/transaction_status.html", context)

    return render(request, "account/home.html", context)

# Category view
def category_summary(request):
    form = CategoryForm(request.GET or None)
    chart_data = {}
    table_data = {}

    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        
        transactions = Transaction.objects.filter(date__range=[start_date, end_date])

        # Group transactions by account and category
        grouped_data = defaultdict(lambda: defaultdict(float))
        for txn in transactions:
            if txn.money_out > 0:
                grouped_data[str(txn.account)][txn.category] += txn.money_out

        # Sort each account's categories by amount (descending)
        for account in grouped_data:
            grouped_data[account] = OrderedDict(
                sorted(grouped_data[account].items(), key=lambda x: x[1], reverse=True)
            )

        # Prepare chart and table data
        for i, (account, categories) in enumerate(grouped_data.items()):
            labels = list(categories.keys())
            values = list(categories.values())
            colors = get_random_colors(len(labels))

            # Chart data (values as raw numbers for Chart.js)
            chart_data[account] = {
                'i': i,
                'labels': labels,
                'data': values,
                'colors': colors
            }

            # Table data (formatted as ₹)
            table_data[account] = [
                (category, format_inr(amount)) for category, amount in categories.items()
            ]

    return render(request, 'account/category.html', {
        'form': form,
        'chart_data': chart_data,
        'table_data': table_data,
        'chart_data_json': json.dumps(chart_data),
        'view_type': form.cleaned_data.get('view_type', 'chart') if form.is_valid() else 'chart'
    })


# Transaction view
def transaction_summary(request):
    form = DateRangeForm(request.GET or None)
    account_names = None
    transactions_by_account = None

    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        transactions_by_account = dict()
        
        transactions = Transaction.objects.filter(date__range=[start_date, end_date]).exclude(money_out=0)
        account_names = transactions.values_list("account__name", flat=True).distinct()

        for account in account_names:
            object_list = Transaction.objects.filter(
                account__name=account,
                date__range=[start_date, end_date]
            ).exclude(money_out=0).order_by('-money_out')[:10]

            txns_formatted = []
            for txn in object_list:
                txn.money_out = format_inr(txn.money_out)
                txns_formatted.append(txn)

            transactions_by_account[account] = txns_formatted

    return render(request, 'account/transactions.html', {
        "form": form,
        "account_names": account_names,
        "transactions_by_account": transactions_by_account
    })

def category_spending_trend(request):
    form = CategoryTrendForm(request.GET or None)
    periods, datasets = [], []

    if form.is_valid():
        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]
        group_by = form.cleaned_data["group_by"]

        transactions = Transaction.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            money_out__gt=0
        )

        # Top 10 categories
        top_categories = (
            transactions
            .values("category")
            .annotate(total_spent=Sum("money_out"))
            .order_by("-total_spent")[:10]
        )
        top_category_names = [cat["category"] for cat in top_categories]

        # Filter for top categories only
        filtered = transactions.filter(category__in=top_category_names)

        # Group by month or year
        date_group = TruncYear("date") if group_by == "year" else TruncMonth("date")

        grouped_data = (
            filtered
            .annotate(period=date_group)
            .values("period", "category")
            .annotate(total_spent=Sum("money_out"))
            .order_by("period")
        )

        # Build x-axis labels
        periods = sorted(list({
            entry["period"].strftime("%Y-%m") if group_by == "month" else entry["period"].strftime("%Y")
            for entry in grouped_data
        }))

        # Build datasets for Chart.js
        for category in top_category_names:
            data = []
            for period in periods:
                match = next((g["total_spent"] for g in grouped_data
                              if g["category"] == category and
                              (g["period"].strftime("%Y-%m") if group_by == "month" else g["period"].strftime("%Y")) == period), 0)
                data.append(match)
            datasets.append({
                "label": category,
                "data": data,
                "fill": False,
            })

    context = {
        "form": form,
        "periods": json.dumps(periods),   # <-- serialize to JSON
        "datasets": json.dumps(datasets)  # <-- serialize to JSON
    }
    return render(request, "account/category_spending_trend.html", context)

def fetch_savings_in_father_account(sheet_id):
    sheet_name = os.environ.get("SAVINGS_IN_FATHER_ACCOUNT_SHEET_NAME")
    df = fetch_google_sheet(sheet_id, sheet_name)
    df["Account Number"] = df["Account Number"].apply(lambda x: str(int(x)) if pd.notnull(x) else "")
    df = df.rename(columns={"Savings In Father Account Account": "Account"})
    df = df.fillna("")
    df_clean = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    exclude_columns = ["Document"]
    df_filtered = df_clean.drop(columns=exclude_columns)
    return df_filtered

def fetch_savings_in_personl_account(sheet_id):
    sheet_name = os.environ.get("SAVINGS_IN_PERSONAL_ACCOUNT_SHEET_NAME")
    df = fetch_google_sheet(sheet_id, sheet_name)
    df["Account Number"] = df["Account Number"].apply(lambda x: str(int(x)) if pd.notnull(x) else "")
    df = df.rename(columns={"Savings Account Account": "Account"})
    df = df.fillna("")
    df_clean = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    exclude_columns = ["Document"]
    df_filtered = df_clean.drop(columns=exclude_columns)
    return df_filtered

def fetch_savings_in_gold(sheet_id):
    sheet_name = os.environ.get("SAVINGS_IN_GOLD")
    df = fetch_google_sheet(sheet_id, sheet_name)
    df = df.rename(columns={"Gold Saving Date": "Date"})
    df = df.fillna("")
    df_clean = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    return df_clean

def fetch_mutual_funds(sheet_id):
    sheet_name = os.environ.get("SAVINGS_IN_MUTUAL_FUNDS")
    df = fetch_google_sheet(sheet_id, sheet_name)
    df = df.rename(columns={"Mutual Funds Profile Fund Name": "Fund Name"})
    df = df.fillna("")
    return df

def fetch_lic(sheet_id):
    sheet_name = os.environ.get("SAVINGS_IN_LIC")
    df = fetch_google_sheet(sheet_id, sheet_name)
    df = df.rename(columns={"LIC Account": "Account"})
    df = df.fillna("")
    df_clean = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    columns_to_keep = ['Premium Year', 'Premium Date', 'Balance', 'Paid']
    df_filtered = df_clean[columns_to_keep]
    df_filtered = df_filtered[df_filtered['Paid'] == 'Yes']
    df_filtered["Premium Year"] = df_filtered["Premium Year"].astype(int)
    exclude_columns = ["Paid"]
    df_filtered = df_filtered.drop(columns=exclude_columns)
    return df_filtered


def saving_view(request):
    context = dict() 
    object_list = list()
    sheet_id = os.environ.get("SHEET_ID")
    
    # Savings In Father Account
    df_filtered = fetch_savings_in_father_account(sheet_id)
    total_row = df_filtered[df_filtered['Account'] == 'Total'].iloc[0]
    nums = [
        float(str(x).replace(',', '')) 
        for x in total_row if isinstance(x, (int, float, str)) and str(x).replace(',', '').replace('.', '').isdigit()
    ]
    minimum_total, maximum_total = nums[:2]
    saving_obj = {
        "saving_type": "Savings In Parents Account",
        "html_view": df_filtered.to_html(classes="table table-striped", index=False)
    }
    object_list.append(saving_obj)
    
    # Savings In Personal Account
    df_filtered = fetch_savings_in_personl_account(sheet_id)
    total_row = df_filtered[df_filtered['Account'] == 'Total'].iloc[0]
    nums = [
        float(str(x).replace(',', '')) 
        for x in total_row if isinstance(x, (int, float, str)) and str(x).replace(',', '').replace('.', '').isdigit()
    ]
    current_minimum_total, current_maximum_total = nums[:2] 
    minimum_total = minimum_total + current_minimum_total
    maximum_total = maximum_total + current_maximum_total
    saving_obj = {
        "saving_type": "Savings In Personal Account",
        "html_view": df_filtered.to_html(classes="table table-striped", index=False)
    }
    object_list.append(saving_obj)

    # Savings in Gold
    df_clean = fetch_savings_in_gold(sheet_id)
    columns_to_keep = ['Date', 'Gold Type', 'Gross Weight', 'Gold Rate per gm', 'Purchased Amount']
    df_filtered = df_clean[columns_to_keep]
    df_filtered = df_filtered.dropna(how='all')
    df_filtered = df_filtered[df_filtered['Date'].notna() & (df_filtered['Date'] != '')]
    savings_in_gold_html = df_filtered.to_html(classes="table table-striped", index=False)
    columns_to_keep = ['Overview', 'Value']
    df_filtered = df_clean[columns_to_keep]
    current_value = df_filtered.loc[df_filtered['Overview'] == 'Current Value', 'Value'].values[0]
    selling_amount = df_filtered.loc[df_filtered['Overview'] == 'Selling Amount', 'Value'].values[0]
    selling_amount = float(selling_amount.replace(',', ''))
    current_value = float(current_value.replace(',', ''))
    minimum_total = minimum_total + selling_amount
    maximum_total = maximum_total + current_value
    saving_obj = {
        "saving_type": "Savings In Gold",
        "html_view": savings_in_gold_html
    }
    object_list.append(saving_obj)

    # Savings in Mutual Funds
    df = fetch_mutual_funds(sheet_id)
    df_selected = df.iloc[0:8, 8:16] 
    columns_to_keep = ['Fund Name', 'Deposited Amount', 'Purchased Units', 'Current Value', 'Profit / Loss', 'Percentage Change']
    mf_purchased_value = df.iloc[1, 21]
    mf_current_value = df.iloc[1, 22]
    mf_current_value = float(mf_current_value.replace(',', ''))
    mf_purchased_value = float(mf_purchased_value.replace(',', ''))
    minimum_total = minimum_total + mf_current_value
    maximum_total = maximum_total + mf_purchased_value
    saving_obj = {
        "saving_type": "Savings In Mutual Funds",
        "html_view": df_selected.to_html(classes="table table-striped", index=False)
    }
    object_list.append(saving_obj)

    # Savings in LIC
    df_filtered = fetch_lic(sheet_id)
    saving_obj = {
        "saving_type": "Savings In LIC",
        "html_view": df_filtered.to_html(classes="table table-striped", index=False)
    }
    object_list.append(saving_obj)

    context = {
        "object_list": object_list,
        "minimum_total": format_inr(minimum_total),
        "maximum_total": format_inr(maximum_total)
    }

    return render(request, 'account/saving.html', context)

									