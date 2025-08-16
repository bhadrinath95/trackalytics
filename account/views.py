from django.shortcuts import render
from .models import Transaction, Bank
from .forms import DateRangeForm, CategoryForm, CategoryTrendForm, SpecificCategoryForm
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
from django.utils.timezone import now
from dateutil.relativedelta import relativedelta

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
        "title": "Top 10 Transactions",
        "form": form,
        "account_names": account_names,
        "transactions_by_account": transactions_by_account
    })

# Transaction view
def transaction_summary_by_category(request):
    sheet_id = os.environ.get("SHEET_ID")
    sheet_name = os.environ.get("DROP_DOWN")
    df = fetch_google_sheet(sheet_id, sheet_name, None)
    first_col = df.iloc[:, 0]
    categories = first_col.dropna()
    categories = categories[categories.astype(str).str.strip()  != ""].tolist()
    
    form = SpecificCategoryForm(request.GET or None, categories=categories)
    account_names = None
    transactions_by_account = None

    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        category = form.cleaned_data.get('category')
        transactions_by_account = dict()
        
        transactions = Transaction.objects.filter(date__range=[start_date, end_date]).exclude(money_out=0)

        if category:
            transactions = transactions.filter(category=category)

        account_names = transactions.values_list("account__name", flat=True).distinct()

        for account in account_names:
            if category:  
                object_list = Transaction.objects.filter(
                    account__name=account,
                    date__range=[start_date, end_date],
                    category=category
                ).exclude(money_out=0).order_by('-money_out')
            else:
                object_list = Transaction.objects.filter(
                    account__name=account,
                    date__range=[start_date, end_date]
                ).exclude(money_out=0).order_by('-money_out')
            

            txns_formatted = []
            for txn in object_list:
                txn.money_out = format_inr(txn.money_out)
                txns_formatted.append(txn)

            transactions_by_account[account] = txns_formatted

    return render(request, 'account/transactions.html', {
        "title": "Transactions By Category",
        "form": form,
        "account_names": account_names,
        "transactions_by_account": transactions_by_account
    })


def income_summary(request):
    form = CategoryTrendForm(request.GET or None)
    chart_data = dict()

    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        group_by = form.cleaned_data["group_by"]

        transactions = Transaction.objects.filter(
            date__range=[start_date, end_date],
            category="[Salary]"
            )
        
        if group_by == "month":
            transactions = transactions.annotate(period=TruncMonth('date'))
            period_format = "%b %Y"  # e.g., "Aug 2025"
        else:
            transactions = transactions.annotate(period=TruncYear('date'))
            period_format = "%Y"  # e.g., "2025"

        summary = transactions.values('period').annotate(total_money_in=Sum('money_in')).order_by('period')

        chart_data = {
            'labels': [entry['period'].strftime(period_format) for entry in summary],
            'data': [entry['total_money_in'] for entry in summary]
        }

    return render(request, 'account/income_summary.html', {
        "form": form,
        "chart_data": chart_data
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
        "periods": json.dumps(periods),
        "datasets": json.dumps(datasets)
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

def account_category_analysis(request):
    total_average = 0
    current_month_average = 0
    total_average_without_saving = 0
    current_month_average_without_saving = 0
    one_year_ago = now().date() - relativedelta(years=1)

    # Fetch transactions
    transactions = Transaction.objects.filter(
        money_out__gt=0, date__gte=one_year_ago
    ).values(
        'account__name', 'account__is_active', 'date', 'category', 'money_out'
    )

    last_salary = (
        Transaction.objects
        .filter(account__name="HDFC Savings", category="[Salary]")
        .order_by('-date')
        .first()
    )

    df = pd.DataFrame(transactions)

    if df.empty:
        return render(request, "analysis.html", {"analysis": {}})

    # Clean data
    df = df[df['account__is_active'] == True]
    df = df[~df['category'].isin(['[Transfer]'])]
    df['date'] = pd.to_datetime(df['date'])
    df['year_month'] = df['date'].dt.to_period('M')

    current_month = now().strftime('%Y-%m')
    analysis = {}
    df_filtered_global = pd.DataFrame(columns=['Category', 'Average'])

    # Define 12-month range
    all_months = pd.period_range(start=one_year_ago, end=now().date(), freq='M')

    for account, acc_df in df.groupby('account__name'):
        # Sum by category & month
        monthly = acc_df.groupby(['category', 'year_month'])['money_out'].sum().reset_index()

        # Expand with missing months = 0
        categories = monthly['category'].unique()
        full_index = pd.MultiIndex.from_product([categories, all_months], names=['category', 'year_month'])
        monthly_full = monthly.set_index(['category', 'year_month']).reindex(full_index, fill_value=0).reset_index()

        # Current month spending
        current = monthly_full[monthly_full['year_month'].astype(str) == current_month]
        current_dict = dict(zip(current['category'], current['money_out']))

        # Average across ALL 12 months
        avg_dict = (monthly_full.groupby('category')['money_out'].sum() / len(all_months)).to_dict()

        # Merge into DataFrame
        merged_df = pd.DataFrame({
            'Category': list(avg_dict.keys()),
            'Current_Month': [current_dict.get(cat, 0) for cat in avg_dict.keys()],
            'Average': list(avg_dict.values())
        }).round(2)

        tbl_merged_df = merged_df[merged_df['Current_Month'] > 0]

        if len(tbl_merged_df) > 0:
            analysis[account] = tbl_merged_df

        # Exclude savings
        merged_df_without_saving = merged_df[~merged_df['Category'].isin(["[Saving]"])]

        # Collect global averages (numeric values only)
        df_filtered = merged_df[['Category', 'Average']]
        df_filtered_global = pd.concat([df_filtered_global, df_filtered], ignore_index=True)

        # Totals
        total_average += merged_df['Average'].sum()
        current_month_average += merged_df['Current_Month'].sum()

        total_average_without_saving += merged_df_without_saving['Average'].sum()
        current_month_average_without_saving += merged_df_without_saving['Current_Month'].sum()

    # Global sum by category (keep numeric until final step)
    df_filtered_global = df_filtered_global.groupby("Category", as_index=False)["Average"].sum()

    # Sort by numeric values
    df_filtered_global = df_filtered_global.sort_values(by="Average", ascending=False)

    # Format INR for display
    df_filtered_global["Average"] = df_filtered_global["Average"].apply(format_inr)

    df_filtered_global_html_view = df_filtered_global.to_html(classes="table table-striped", index=False)
    
    context = {
        "analysis": analysis,
        "last_salary": last_salary.money_in if last_salary else 0,
        "total_average": round(total_average, 2),
        "current_month_average": round(current_month_average, 2),
        "total_average_without_saving": round(total_average_without_saving, 2),
        "current_month_average_without_saving": round(current_month_average_without_saving, 2),
        "df_filtered_global_html_view": df_filtered_global_html_view
    }
    return render(request, "account/analysis.html", context)