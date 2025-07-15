from django.shortcuts import render
from .models import Transaction
from .forms import DateRangeForm
from collections import defaultdict
import random

# Create your views here.
def transaction_view(request):
    qs = Transaction.objects.all()
    context = {
        "object_list": qs
    }
    return render(request, "account/home.html", context=context)

def get_random_colors(n):
    colors = []
    for _ in range(n):
        color = f'#{random.randint(0, 0xFFFFFF):06x}'
        colors.append(color)
    return colors

def transaction_summary(request):
    form = DateRangeForm(request.GET or None)
    chart_data = {}

    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']

        transactions = Transaction.objects.filter(date__range=[start_date, end_date])

        grouped_data = defaultdict(lambda: defaultdict(float))

        for txn in transactions:
            if txn.money_out > 0:
                grouped_data[txn.account][txn.category] += txn.money_out

        for account, categories in grouped_data.items():
            labels = list(categories.keys())
            data = list(categories.values())
            colors = get_random_colors(len(labels))
            chart_data[account] = {
                'labels': labels,
                'data': data,
                'colors': colors

            }

    return render(request, 'account/summary.html', {
        'form': form,
        'chart_data': chart_data
    })
