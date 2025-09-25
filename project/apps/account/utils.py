from django.db import transaction
from django.contrib.auth.models import User
from django.apps import apps
from typing import List, Dict, Optional, Tuple
from project.apps.account.models import Account


class AccountTreeManager:
    """账户树管理器"""
    
    @staticmethod
    def get_account_tree(user: User, account_type: Optional[str] = None) -> List[Dict]:
        """
        获取用户的账户树结构
        
        Args:
            user: 用户对象
            account_type: 账户类型过滤（可选）
        
        Returns:
            树形结构的账户列表
        """
        queryset = Account.objects.filter(owner=user)
        
        if account_type:
            queryset = queryset.filter(account__startswith=account_type)
        
        # 获取根账户
        root_accounts = queryset.filter(parent__isnull=True).order_by('account')
        
        def build_tree(accounts):
            result = []
            for account in accounts:
                account_data = {
                    'id': account.id,
                    'account': account.account,
                    'account_type': account.get_account_type(),
                    'currencies': [{'id': c.id, 'code': c.code, 'name': c.name} for c in account.currencies.all()],
                    'has_children': account.has_children(),
                    'mapping_count': AccountTreeManager.get_mapping_count(account),
                    'children': []
                }
                
                # 递归获取子账户
                children = queryset.filter(parent=account).order_by('account')
                if children.exists():
                    account_data['children'] = build_tree(children)
                
                result.append(account_data)
            
            return result
        
        return build_tree(root_accounts)
    
    @staticmethod
    def get_mapping_count(account: Account) -> Dict[str, int]:
        """
        获取账户的映射数量
        
        Args:
            account: 账户对象
        
        Returns:
            包含各类映射数量的字典
        """
        try:
            Expense = apps.get_model('maps', 'Expense')
            Assets = apps.get_model('maps', 'Assets')
            Income = apps.get_model('maps', 'Income')
            
            expense_count = Expense.objects.filter(expend=account, enable=True).count()
            assets_count = Assets.objects.filter(assets=account, enable=True).count()
            income_count = Income.objects.filter(income=account, enable=True).count()
            
            return {
                'expense': expense_count,
                'assets': assets_count,
                'income': income_count,
                'total': expense_count + assets_count + income_count
            }
        except:
            return {'expense': 0, 'assets': 0, 'income': 0, 'total': 0}
    
    @staticmethod
    def get_account_path(account: Account) -> str:
        """
        获取账户的完整路径
        
        Args:
            account: 账户对象
        
        Returns:
            账户的完整路径字符串
        """
        return account.account
    
    @staticmethod
    def get_account_ancestors(account: Account) -> List[Account]:
        """
        获取账户的所有祖先账户
        
        Args:
            account: 账户对象
        
        Returns:
            祖先账户列表（从根到父）
        """
        ancestors = []
        current = account.parent
        
        while current:
            ancestors.insert(0, current)
            current = current.parent
        
        return ancestors
    
    @staticmethod
    def get_account_descendants(account: Account) -> List[Account]:
        """
        获取账户的所有后代账户
        
        Args:
            account: 账户对象
        
        Returns:
            后代账户列表
        """
        descendants = []
        
        def collect_descendants(acc):
            children = Account.objects.filter(parent=acc)
            for child in children:
                descendants.append(child)
                collect_descendants(child)
        
        collect_descendants(account)
        return descendants


class AccountMigrationManager:
    """账户迁移管理器"""
    
    @staticmethod
    @transaction.atomic
    def migrate_account(
        source_account: Account,
        target_account: Account,
        migrate_mappings: bool = True,
        close_source: bool = False
    ) -> Dict:
        """
        迁移账户及其相关数据
        
        Args:
            source_account: 源账户
            target_account: 目标账户
            migrate_mappings: 是否迁移映射
            close_source: 是否关闭源账户
        
        Returns:
            迁移结果字典
        """
        result = {
            'success': True,
            'mappings_migrated': 0,
            'source_closed': False,
            'errors': []
        }
        
        try:
            if migrate_mappings:
                # 迁移映射
                mappings_migrated = AccountMigrationManager._migrate_mappings(
                    source_account, target_account
                )
                result['mappings_migrated'] = mappings_migrated
            
            if close_source:
                # 关闭源账户
                close_result = source_account.close(migrate_to=target_account)
                result['source_closed'] = close_result.get('account_closed', False)
            
            return result
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(str(e))
            raise
    
    @staticmethod
    def _migrate_mappings(source_account: Account, target_account: Account) -> int:
        """
        迁移账户相关的映射
        
        Args:
            source_account: 源账户
            target_account: 目标账户
        
        Returns:
            迁移的映射数量
        """
        try:
            Expense = apps.get_model('maps', 'Expense')
            Assets = apps.get_model('maps', 'Assets')
            Income = apps.get_model('maps', 'Income')
            
            expense_count = Expense.objects.filter(expend=source_account).update(expend=target_account)
            assets_count = Assets.objects.filter(assets=source_account).update(assets=target_account)
            income_count = Income.objects.filter(income=source_account).update(income=target_account)
            
            return expense_count + assets_count + income_count
        except Exception as e:
            raise Exception(f"迁移映射失败: {str(e)}")


class AccountValidator:
    """账户验证器"""
    
    VALID_ROOT_ACCOUNTS = ['Assets', 'Liabilities', 'Equity', 'Income', 'Expenses']
    
    @staticmethod
    def validate_account_path(account_path: str) -> Tuple[bool, str]:
        """
        验证账户路径格式
        
        Args:
            account_path: 账户路径
        
        Returns:
            (是否有效, 错误信息)
        """
        if not account_path:
            return False, "账户路径不能为空"
        
        # 检查路径格式
        parts = account_path.split(':')
        if not all(part.isidentifier() for part in parts):
            return False, "账户路径必须由字母、数字和下划线组成，用冒号分隔"
        
        # 检查根账户类型
        root = parts[0]
        if root not in AccountValidator.VALID_ROOT_ACCOUNTS:
            return False, f"根账户必须是以下之一: {', '.join(AccountValidator.VALID_ROOT_ACCOUNTS)}"
        
        # 检查路径长度
        if len(account_path) > 128:
            return False, "账户路径长度不能超过128个字符"
        
        return True, ""
    
    @staticmethod
    def validate_account_hierarchy(account_path: str, user: User) -> Tuple[bool, str]:
        """
        验证账户层次结构
        
        Args:
            account_path: 账户路径
            user: 用户对象
        
        Returns:
            (是否有效, 错误信息)
        """
        parts = account_path.split(':')
        
        # 检查父账户是否存在
        if len(parts) > 1:
            parent_path = ':'.join(parts[:-1])
            try:
                parent_account = Account.objects.get(account=parent_path, owner=user)
                if not parent_account.enable:
                    return False, f"父账户 {parent_path} 已禁用"
            except Account.DoesNotExist:
                return False, f"父账户 {parent_path} 不存在"
        
        return True, ""
    
    @staticmethod
    def validate_account_uniqueness(account_path: str, user: User, exclude_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        验证账户唯一性
        
        Args:
            account_path: 账户路径
            user: 用户对象
            exclude_id: 排除的账户ID（用于更新时）
        
        Returns:
            (是否有效, 错误信息)
        """
        queryset = Account.objects.filter(account=account_path, owner=user)
        
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        
        if queryset.exists():
            return False, f"账户 {account_path} 已存在"
        
        return True, ""


class AccountStatistics:
    """账户统计工具"""
    
    @staticmethod
    def get_user_account_statistics(user: User) -> Dict:
        """
        获取用户的账户统计信息
        
        Args:
            user: 用户对象
        
        Returns:
            统计信息字典
        """
        accounts = Account.objects.filter(owner=user)
        
        # 按类型统计
        type_stats = {}
        for account_type in AccountValidator.VALID_ROOT_ACCOUNTS:
            type_accounts = accounts.filter(account__startswith=account_type)
            type_stats[account_type] = {
                'total': type_accounts.count(),
                'enabled': type_accounts.filter(enable=True).count(),
                'disabled': type_accounts.filter(enable=False).count()
            }
        
        # 总体统计
        total_accounts = accounts.count()
        enabled_accounts = accounts.filter(enable=True).count()
        disabled_accounts = total_accounts - enabled_accounts
        
        # 有映射的账户数量
        try:
            Expense = apps.get_model('maps', 'Expense')
            Assets = apps.get_model('maps', 'Assets')
            Income = apps.get_model('maps', 'Income')
            
            expense_accounts = set(Expense.objects.filter(owner=user, enable=True).values_list('expend_id', flat=True))
            assets_accounts = set(Assets.objects.filter(owner=user, enable=True).values_list('assets_id', flat=True))
            income_accounts = set(Income.objects.filter(owner=user, enable=True).values_list('income_id', flat=True))
            
            mapped_accounts = len(expense_accounts | assets_accounts | income_accounts)
        except:
            mapped_accounts = 0
        
        return {
            'total_accounts': total_accounts,
            'enabled_accounts': enabled_accounts,
            'disabled_accounts': disabled_accounts,
            'mapped_accounts': mapped_accounts,
            'type_statistics': type_stats
        }
    
    @staticmethod
    def get_account_usage_statistics(account: Account) -> Dict:
        """
        获取账户使用统计
        
        Args:
            account: 账户对象
        
        Returns:
            使用统计字典
        """
        mapping_count = AccountTreeManager.get_mapping_count(account)
        
        # 获取子账户数量
        children_count = account.children.count()
        
        # 获取后代账户数量
        descendants = AccountTreeManager.get_account_descendants(account)
        descendants_count = len(descendants)
        
        return {
            'mapping_count': mapping_count,
            'children_count': children_count,
            'descendants_count': descendants_count,
            'is_leaf': children_count == 0,
            'is_root': account.parent is None
        }
