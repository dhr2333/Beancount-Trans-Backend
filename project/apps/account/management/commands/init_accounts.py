from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from project.apps.account.models import Account


class Command(BaseCommand):
    help = '初始化默认的Beancount账户结构'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='要为其初始化账户的用户名（如果不指定，则为所有用户初始化）',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新创建账户（删除现有账户）',
        )

    def handle(self, *args, **options):
        username = options.get('username')
        force = options.get('force', False)
        
        # 获取用户
        if username:
            try:
                users = [User.objects.get(username=username)]
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'用户 {username} 不存在')
                )
                return
        else:
            users = User.objects.all()
        
        if not users:
            self.stdout.write(
                self.style.WARNING('没有找到任何用户')
            )
            return
        
        # 为每个用户初始化账户
        for user in users:
            self.init_user_accounts(user, force)
        
        self.stdout.write(
            self.style.SUCCESS('账户初始化完成')
        )

    def init_user_accounts(self, user, force=False):
        """为用户初始化默认账户结构"""
        self.stdout.write(f'为用户 {user.username} 初始化账户...')
        
        if force:
            # 删除现有账户
            Account.objects.filter(owner=user).delete()
            self.stdout.write(f'已删除用户 {user.username} 的现有账户')
        
        # 默认账户结构
        default_accounts = [
            # 资产账户
            'Assets:Bank:Checking',
            'Assets:Bank:Savings',
            'Assets:Cash',
            'Assets:Investment:Stocks',
            'Assets:Investment:Bonds',
            'Assets:Investment:Funds',
            'Assets:RealEstate',
            'Assets:Other',
            
            # 负债账户
            'Liabilities:CreditCard',
            'Liabilities:Loan:Personal',
            'Liabilities:Loan:Mortgage',
            'Liabilities:Other',
            
            # 权益账户
            'Equity:Opening-Balances',
            'Equity:Retained-Earnings',
            
            # 收入账户
            'Income:Salary',
            'Income:Investment:Dividends',
            'Income:Investment:Interest',
            'Income:Other',
            
            # 支出账户
            'Expenses:Food:Dining',
            'Expenses:Food:Groceries',
            'Expenses:Transportation:Gas',
            'Expenses:Transportation:Public',
            'Expenses:Housing:Rent',
            'Expenses:Housing:Utilities',
            'Expenses:Healthcare',
            'Expenses:Entertainment',
            'Expenses:Education',
            'Expenses:Other',
        ]
        
        created_count = 0
        for account_path in default_accounts:
            account, created = Account.objects.get_or_create(
                account=account_path,
                owner=user,
                defaults={'enable': True}
            )
            if created:
                created_count += 1
                self.stdout.write(f'  创建账户: {account_path}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'为用户 {user.username} 创建了 {created_count} 个新账户'
            )
        )
