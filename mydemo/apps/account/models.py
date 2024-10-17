from django.db import models
from django.contrib.auth.models import User


from mydemo.models import BaseModel


class Account(BaseModel):
    STATUS = (
        ('open', 'open'),
        ('close', 'close'),
    )
    ACCOUNT_TYPE = (
        ("assets", "资产账户"),
        ("equity", "平衡账户"),
        ("expenses", "支出账户"),
        ("income", "收入账户"),
        ("Liabilities", "负债账户"),
    )

    date = models.DateField(max_length=16, help_text="开/闭户日期", verbose_name="日期")
    status = models.CharField(max_length=8, choices=STATUS, help_text="状态", verbose_name="状态")
    account = models.CharField(max_length=64, help_text="账户", verbose_name="账户")
    currency = models.CharField(max_length=16, null=True, help_text="货币(可为空)", verbose_name="货币")
    note = models.CharField(max_length=16, null=True, help_text="备注(可为空)", verbose_name="备注")
    account_type = models.CharField(max_length=16, choices=ACCOUNT_TYPE,
                                    help_text="交易类型(Beancount五个类型账户之一)", verbose_name="交易类型")
    owner = models.ForeignKey(User, related_name='account', on_delete=models.CASCADE, db_index=True, help_text="属主",
                              verbose_name="属主")

    class Meta:
        app_label = 'account_config'
        ordering = ['account_type']
        verbose_name = '账本账户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.account
