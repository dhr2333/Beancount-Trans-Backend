from django.db import models


# Create your models here.

class Expense_Map(models.Model):
    key = models.CharField(max_length=16, unique=True, null=False)
    payee = models.CharField(max_length=8, null=True)
    payee_order = models.IntegerField(default=100)
    expend = models.CharField(max_length=64, default="Expenses:Other", null=False)
    tag = models.CharField(max_length=16)
    classification = models.CharField(max_length=16)


class Assets_Map(models.Model):
    key = models.CharField(max_length=16, unique=True, null=False)
    full = models.CharField(max_length=16, null=False)
    income = models.CharField(max_length=64, default="Income:Other", null=False)
