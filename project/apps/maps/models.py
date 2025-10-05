from django.db import models
from django.contrib.auth.models import User

from project.apps.account.models import Account, Currency
from project.models import BaseModel


class Expense(BaseModel):
    key = models.CharField(max_length=16, null=False, help_text="关键字")
    payee = models.CharField(max_length=32, null=True, blank=True, help_text="收款方")
    expend = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True, help_text="支出账户")
    owner = models.ForeignKey(User, related_name='expense', on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=True, blank=True, help_text="货币")
    enable = models.BooleanField(default=True, verbose_name="是否启用", help_text="启用状态")

    class Meta:
        db_table = 'maps_expense'
        verbose_name = '支出映射'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.key

    def save(self, *args, **kwargs):
        """保存时同步货币到关联账户"""
        super().save(*args, **kwargs)
        # 将映射的货币添加到关联的账户中
        if self.expend and self.currency:
            self.expend.currencies.add(self.currency)


class Assets(BaseModel):
    key = models.CharField(max_length=16, null=False, help_text="关键字")
    full = models.CharField(max_length=16, null=False, help_text="账户名称")
    assets = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True, help_text="资产账户")
    owner = models.ForeignKey(User, related_name='assets', on_delete=models.CASCADE)
    enable = models.BooleanField(default=True, verbose_name="是否启用", help_text="启用状态")

    class Meta:
        db_table = 'maps_assets'
        verbose_name = '资产映射'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.full


class Income(BaseModel):
    key = models.CharField(max_length=16, null=False, help_text="关键字")
    payer = models.CharField(max_length=8, null=True, blank=True, help_text="付款方")
    income = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True, help_text="收入账户")
    owner = models.ForeignKey(User, related_name='income', on_delete=models.CASCADE)
    enable = models.BooleanField(default=True, verbose_name="是否启用", help_text="启用状态")

    class Meta:
        db_table = 'maps_income'
        verbose_name = '收入映射'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.key


class Template(BaseModel):
    name = models.CharField(max_length=32, null=False, help_text="模板名称")
    description = models.TextField(blank=True, help_text="模板描述")
    type = models.CharField(choices=[('expense', '支出'), ('income', '收入'), ('assets', '资产')], max_length=16, help_text="模板类型")
    is_public = models.BooleanField(default=False, help_text="是否公开")
    is_official = models.BooleanField(default=False, help_text="是否官方")
    version = models.CharField(max_length=16, blank=True, default="1.0.0", help_text="版本号")
    update_notes = models.TextField(null=True, blank=True, help_text="更新说明")
    owner = models.ForeignKey(User, related_name='templates', on_delete=models.CASCADE)

    class Meta:
        db_table = 'maps_template'
        verbose_name = '映射模板'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'owner', 'type'],
                name='unique_template_per_user_type'
            )
        ]
    def __str__(self):
        return self.name


class TemplateItem(BaseModel):
    template = models.ForeignKey(Template, related_name='items', on_delete=models.CASCADE)
    key = models.CharField(max_length=16, null=False, help_text="关键字")
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True, help_text="映射账户")
    payee = models.CharField(max_length=32, null=True, blank=True, help_text="收款方")
    payer = models.CharField(max_length=32, null=True, blank=True, help_text="付款方")
    full = models.CharField(max_length=32, null=True, blank=True, help_text="账户全称")
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=True, blank=True, help_text="货币")

    class Meta:
        db_table = 'maps_template_item'
        verbose_name = '模板项'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['template', 'key'],
                name='unique_key_per_template'
            )
        ]

    def __str__(self):
        return f"{self.template.name} - {self.key}"
