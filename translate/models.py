from django.db import models


# Create your models here.

class Expense_Map(models.Model):
    key = models.CharField(max_length=16, unique=True, null=False, help_text="关键字")
    payee = models.CharField(max_length=8, null=True, help_text="商家")
    payee_order = models.IntegerField(default=100, help_text="优先级")
    expend = models.CharField(max_length=64, default="Expenses:Other", null=False, help_text="支出账户")
    tag = models.CharField(max_length=16, help_text="标签")
    classification = models.CharField(max_length=16, help_text="归类")

    class Meta:
        db_table = 'translate_expense_map'
        verbose_name = '支出映射'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.key


class Assets_Map(models.Model):
    key = models.CharField(max_length=16, unique=True, null=False, help_text="关键字")
    full = models.CharField(max_length=16, null=False, help_text="账户名称")
    income = models.CharField(max_length=64, default="Income:Other", null=False, help_text="收入账户")

    class Meta:
        db_table = 'translate_assets_map'
        verbose_name = '收入映射'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.full
