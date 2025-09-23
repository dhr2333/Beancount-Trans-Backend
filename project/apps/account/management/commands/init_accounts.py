from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from project.apps.account.models import Account, Currency


class Command(BaseCommand):
    help = '初始化默认的Beancount账户结构和货币'

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
        
        # 初始化货币
        self.init_currencies()
        
        # 为每个用户初始化账户
        for user in users:
            self.init_user_accounts(user, force)
        
        self.stdout.write(
            self.style.SUCCESS('账户初始化完成')
        )

    def init_currencies(self):
        """初始化默认货币"""
        default_currencies = [
            {'code': 'CNY', 'name': '人民币'},
            {'code': 'USD', 'name': '美元'},
            {'code': 'EUR', 'name': '欧元'},
            {'code': 'JPY', 'name': '日元'},
            {'code': 'GBP', 'name': '英镑'},
            {'code': 'HKD', 'name': '港币'},
        ]
        
        for currency_data in default_currencies:
            currency, created = Currency.objects.get_or_create(
                code=currency_data['code'],
                defaults={'name': currency_data['name']}
            )
            if created:
                self.stdout.write(f'创建货币: {currency.code} - {currency.name}')
            else:
                self.stdout.write(f'货币已存在: {currency.code} - {currency.name}')

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
