from django.db import models

# Create your models here.
class Bank(models.Model):
    name = models.CharField(max_length=30)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
class Transaction(models.Model):
    account = models.ForeignKey(Bank, blank=True, null=True, on_delete=models.SET_NULL)
    date = models.DateField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(null=True, blank=True)
    money_in = models.FloatField(null=True, blank=True)
    money_out = models.FloatField(null=True, blank=True)
    account_balance = models.FloatField(null=True, blank=True)