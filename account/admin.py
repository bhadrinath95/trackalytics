from django.contrib import admin
from .models import Bank, Transaction

# Register your models here.
class BankAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'is_active']

class TransactionAdmin(admin.ModelAdmin):
    list_display = ['date', 'description', 'category', 'money_in', 'money_out', 'account_balance']
    search_fields = ['account', 'description']
    raw_id_fields = ['account']

admin.site.register(Bank, BankAdmin)
admin.site.register(Transaction, TransactionAdmin)