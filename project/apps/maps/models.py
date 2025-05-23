from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import User


from project.models import BaseModel


# Create your models here.


class Expense(BaseModel):
    key = models.CharField(max_length=16, null=False, help_text="关键字")
    payee = models.CharField(max_length=32, null=True, help_text="收款方")
    expend = models.CharField(max_length=64, default="Expenses:Other", null=False, help_text="支出账户")
    owner = models.ForeignKey(User, related_name='expense', on_delete=models.CASCADE)
    currency = models.CharField(
        max_length=24,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z][A-Z0-9\'._-]{0,22}([A-Z0-9])?$',
                message='货币必须以大写字母开头，以大写字母/数字结尾，并且只能包含 [A-Z0-9\'._-]'
            )
        ],
      help_text="货币"
    )
    enable = models.BooleanField(default=True,verbose_name="是否启用",help_text="启用状态")

    class Meta:
        db_table = 'maps_expense'
        verbose_name = '支出映射'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.key

    def clean(self):
        """自动转换格式：确保首字母大写，其他字母转为大写，符号和数字不变"""
        if self.currency:
            # 首字母大写
            first_char = self.currency[0].upper() if self.currency else ''
            remaining = ''.join([c.upper() if c.isalpha() else c for c in self.currency[1:]])
            self.currency = first_char + remaining
        super().clean()


class Assets(BaseModel):
    key = models.CharField(max_length=16, null=False, help_text="关键字")
    full = models.CharField(max_length=16, null=False, help_text="账户名称")
    assets = models.CharField(max_length=64, default="Assets:Other:Test", null=False, help_text="资产账户")
    owner = models.ForeignKey(User, related_name='assets', on_delete=models.CASCADE)
    enable = models.BooleanField(default=True,verbose_name="是否启用",help_text="启用状态")


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
    enable = models.BooleanField(default=True,verbose_name="是否启用",help_text="启用状态")

    class Meta:
        db_table = 'maps_income'
        verbose_name = '收入映射'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.key

