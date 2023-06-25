from django.db import models


# Create your models here.

class Expense_Map(models.Model):
    key = models.CharField(max_length=16, unique=True, null=False, help_text="关键字")
    payee = models.CharField(max_length=8, null=True)
    payee_order = models.IntegerField(default=100)
    expend = models.CharField(max_length=64, default="Expenses:Other", null=False)
    tag = models.CharField(max_length=16)
    classification = models.CharField(max_length=16)

    class Meta:
        db_table = 'translate_expense_map'
        verbose_name = '支出映射'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.key


class Assets_Map(models.Model):
    key = models.CharField(max_length=16, unique=True, null=False)
    full = models.CharField(max_length=16, null=False)
    income = models.CharField(max_length=64, default="Income:Other", null=False)
