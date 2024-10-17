from django.db import models
from django.contrib.auth.models import User


from mydemo.models import BaseModel


# Create your models here.


class Expense(BaseModel):
    key = models.CharField(max_length=16, null=False, help_text="关键字")
    payee = models.CharField(max_length=8, null=True, help_text="收款方")
    expend = models.CharField(max_length=64, default="Expenses:Other", null=False, help_text="支出账户")
    owner = models.ForeignKey(User, related_name='expense', on_delete=models.CASCADE)

    class Meta:
        db_table = 'maps_expense'
        verbose_name = '支出映射'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.key


class Assets(BaseModel):
    key = models.CharField(max_length=16, null=False, help_text="关键字")
    full = models.CharField(max_length=16, null=False, help_text="账户名称")
    assets = models.CharField(max_length=64, default="Assets:Other:Test", null=False, help_text="资产账户")
    owner = models.ForeignKey(User, related_name='assets', on_delete=models.CASCADE)

    class Meta:
        db_table = 'maps_assets'
        verbose_name = '资产映射'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.full


class Income(BaseModel):
    key = models.CharField(max_length=16, null=False, help_text="关键字")
    payer = models.CharField(max_length=8, null=True, help_text="付款方")
    income = models.CharField(max_length=64, default="Income:Other", null=False, help_text="收入账户")
    owner = models.ForeignKey(User, related_name='income', on_delete=models.CASCADE)

    class Meta:
        db_table = 'maps_income'
        verbose_name = '收入映射'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.key
