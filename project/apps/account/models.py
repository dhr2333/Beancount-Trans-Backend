from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from project.models import BaseModel


class Currency(BaseModel):
    code = models.CharField(
        max_length=24,
        validators=[
            RegexValidator(
                regex=r'^[A-Z][A-Z0-9\'._-]{0,22}([A-Z0-9])?$',
                message='货币必须以大写字母开头，以大写字母/数字结尾，并且只能包含 [A-Z0-9\'._-]'
            )
        ],                            
        verbose_name="货币代码",
        help_text="货币代码"
        )
    name = models.CharField(max_length=32, verbose_name="货币名称")
    owner = models.ForeignKey(User, related_name='currencies', on_delete=models.CASCADE, db_index=True, help_text="属主", verbose_name="属主")

    class Meta:
        verbose_name = '货币'
        verbose_name_plural = verbose_name
        unique_together = ['code', 'owner']

    def __str__(self):
        return self.code


class Account(BaseModel):
    account = models.CharField(max_length=128, help_text="账户路径", verbose_name="账户")
    currencies = models.ManyToManyField(Currency, blank=True, help_text="货币", verbose_name="货币")
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children', help_text="父账户", verbose_name="父账户")
    owner = models.ForeignKey(User, related_name='accounts', on_delete=models.CASCADE, db_index=True, help_text="属主", verbose_name="属主")
    enable = models.BooleanField(default=True,verbose_name="是否启用",help_text="启用状态")

    class Meta:
        unique_together = ['account', 'owner']
        ordering = ['account']
        verbose_name = '账本账户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.account

    def clean(self):
        if not all(part.isidentifier() for part in self.account.split(':')):
            raise ValidationError("账户路径必须由字母、数字和下划线组成，用冒号分隔")
        
    def save(self, *args, **kwargs):
        """保存账户时自动创建父账户，并同步映射状态"""
        # 检查enable字段是否发生变化
        enable_changed = False
        if self.pk:
            try:
                old_instance = Account.objects.get(pk=self.pk)
                enable_changed = old_instance.enable != self.enable
            except Account.DoesNotExist:
                pass
        
        if not self.parent and ':' in self.account:
            parent_account_path = ':'.join(self.account.split(':')[:-1])
            try:
                # 尝试获取已存在的父账户
                self.parent = Account.objects.get(account=parent_account_path, owner=self.owner)
            except Account.DoesNotExist:
                # 自动创建父账户
                self.parent = self._create_parent_account(parent_account_path)
        
        super().save(*args, **kwargs)
        
        # 如果enable状态发生变化，同步更新相关映射
        if enable_changed:
            self._sync_mappings_enable_status()
    
    def _create_parent_account(self, parent_account_path):
        """递归创建父账户"""
        try:
            # 尝试获取父账户
            parent = Account.objects.get(account=parent_account_path, owner=self.owner)
            return parent
        except Account.DoesNotExist:
            # 如果父账户不存在，递归创建
            if ':' in parent_account_path:
                # 还有更上级的父账户，先创建上级父账户
                grandparent_path = ':'.join(parent_account_path.split(':')[:-1])
                grandparent = self._create_parent_account(grandparent_path)
                
                # 创建当前父账户
                parent = Account.objects.create(
                    account=parent_account_path,
                    owner=self.owner,
                    parent=grandparent,
                    enable=True
                )
            else:
                # 这是根级账户，直接创建
                parent = Account.objects.create(
                    account=parent_account_path,
                    owner=self.owner,
                    enable=True
                )
            
            return parent

    def _sync_mappings_enable_status(self):
        """同步映射的启用状态与账户状态"""
        # 避免循环导入，使用字符串引用模型
        from django.apps import apps
        
        try:
            # 获取映射模型
            Expense = apps.get_model('maps', 'Expense')
            Assets = apps.get_model('maps', 'Assets')
            Income = apps.get_model('maps', 'Income')
            
            # 同步所有相关映射的启用状态
            Expense.objects.filter(expend=self).update(enable=self.enable)
            Assets.objects.filter(assets=self).update(enable=self.enable)
            Income.objects.filter(income=self).update(enable=self.enable)
            
        except Exception as e:
            # 记录错误但不阻止账户保存
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"同步映射状态失败: {str(e)}")

    def has_children(self):
        """检查是否存在子账户"""
        return self.children.exists()

    def get_account_type(self):
        """获取账户类型"""
        root = self.account.split(':')[0]
        type_mapping = {
            'Assets': '资产账户',
            'Liabilities': '负债账户', 
            'Equity': '权益账户',
            'Income': '收入账户',
            'Expenses': '支出账户'
        }
        return type_mapping.get(root, '未知类型')
    
    def close(self, migrate_to=None):
        """
        关闭账户，并处理所有相关的映射
        
        Args:
            migrate_to: 迁移目标账户，如果提供，则将相关映射迁移到此账户
        Returns:
            dict: 包含操作结果的字典
        """
        # 避免循环导入，使用字符串引用模型
        from django.apps import apps
        
        # 获取映射模型
        Expense = apps.get_model('maps', 'Expense')
        Assets = apps.get_model('maps', 'Assets')
        Income = apps.get_model('maps', 'Income')
        
        result = {
            'account_closed': True,
            'has_children': self.has_children(),
            'mappings_migrated': False,
            'mappings_disabled': False,
            'migrated_to': None,
            'mapping_counts': {
                'expense': 0,
                'assets': 0,
                'income': 0,
                'total': 0
            }
        }
        
        # 统计当前映射数量
        expense_count = Expense.objects.filter(expend=self).count()
        assets_count = Assets.objects.filter(assets=self).count()
        income_count = Income.objects.filter(income=self).count()
        total_mappings = expense_count + assets_count + income_count
        
        result['mapping_counts'] = {
            'expense': expense_count,
            'assets': assets_count,
            'income': income_count,
            'total': total_mappings
        }
        
        # 处理映射迁移
        if migrate_to:
            # 验证目标账户
            if not migrate_to.enable:
                raise ValidationError("目标账户已禁用，无法进行迁移")
            
            # 迁移所有类型的映射到目标账户
            Expense.objects.filter(expend=self).update(expend=migrate_to)
            Assets.objects.filter(assets=self).update(assets=migrate_to)
            Income.objects.filter(income=self).update(income=migrate_to)
            
            result['mappings_migrated'] = True
            result['migrated_to'] = migrate_to.id
        else:
            # 禁用所有相关映射
            Expense.objects.filter(expend=self).update(enable=False)
            Assets.objects.filter(assets=self).update(enable=False)
            Income.objects.filter(income=self).update(enable=False)
            
            result['mappings_disabled'] = True
        
        # 关闭当前账户（不关闭子账户）
        self.enable = False
        self.save()
        
        return result

    def delete_with_migration(self, migrate_to=None):
        """
        删除账户，并处理所有相关的映射
        
        Args:
            migrate_to: 迁移目标账户，可选，用于迁移相关映射
        Returns:
            dict: 包含操作结果的字典
        """
        # 检查是否有子账户
        if self.has_children():
            raise ValidationError("存在子账户，无法删除。请先处理子账户")
        
        # 避免循环导入，使用字符串引用模型
        from django.apps import apps
        
        # 获取映射模型
        Expense = apps.get_model('maps', 'Expense')
        Assets = apps.get_model('maps', 'Assets')
        Income = apps.get_model('maps', 'Income')
        
        # 统计映射数量
        expense_count = Expense.objects.filter(expend=self).count()
        assets_count = Assets.objects.filter(assets=self).count()
        income_count = Income.objects.filter(income=self).count()
        total_mappings = expense_count + assets_count + income_count
        
        result = {
            'account_deleted': True,
            'mappings_migrated': False,
            'migrated_to': None,
            'mapping_counts': {
                'expense': expense_count,
                'assets': assets_count,
                'income': income_count,
                'total': total_mappings
            }
        }
        
        # 如果有映射数据，必须提供迁移目标
        if total_mappings > 0:
            if not migrate_to:
                raise ValidationError("账户存在映射数据，删除时必须提供迁移目标账户")
            
            # 验证目标账户
            if not migrate_to.enable:
                raise ValidationError("目标账户已禁用，无法进行迁移")
            
            if migrate_to == self:
                raise ValidationError("不能将账户迁移到自身")
            
            # 迁移所有类型的映射到目标账户
            Expense.objects.filter(expend=self).update(expend=migrate_to)
            Assets.objects.filter(assets=self).update(assets=migrate_to)
            Income.objects.filter(income=self).update(income=migrate_to)
            
            result['mappings_migrated'] = True
            result['migrated_to'] = migrate_to.id
        
        # 删除账户
        account_id = self.id
        account_name = self.account
        self.delete()
        
        result['deleted_account'] = {
            'id': account_id,
            'name': account_name
        }
        
        return result
