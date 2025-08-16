# account/utils.py
import pandas as pd
import requests
from io import StringIO
from prophet import Prophet
import pandas as pd
from django.db.models.functions import ExtractYear, ExtractMonth
from .models import Transaction
from datetime import date
from django.db.models import Sum, FloatField
from django.db.models.functions import Coalesce


def clean_money(value):
    try:
        return float(str(value).replace(',', '').strip())
    except (ValueError, TypeError):
        return 0.0

def fetch_google_sheet(sheet_id, sheet_name, header=0):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError("❌ Failed to fetch the Google Sheet.")
    return pd.read_csv(StringIO(response.text), header=header)

def preprocess_transaction_data(df):
    df = df[df['Income and Expense Account'].notna() & (df['Income and Expense Account'] != 'Total')]
    
    df['Income Money IN'] = df['Income Money IN'].fillna("0").apply(clean_money)
    df['Expense Money OUT'] = df['Expense Money OUT'].fillna("0").apply(clean_money)
    df['Account Balance'] = df['Account Balance'].fillna("0").apply(clean_money)
    
    return df