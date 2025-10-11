# project/apps/account/management/commands/init_official_templates.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from project.apps.account.models import Account, AccountTemplate, AccountTemplateItem
from project.apps.maps.models import Template, TemplateItem
from project.apps.translate.models import FormatConfig

User = get_user_model()


class Command(BaseCommand):
    help = '初始化官方模板和默认用户（id=1）的完整数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-admin',
            action='store_true',
            help='跳过创建admin用户（如果已存在）',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新创建模板（删除现有官方模板）',
        )

    def handle(self, *args, **options):
        skip_admin = options.get('skip_admin', False)
        force = options.get('force', False)

        self.stdout.write(self.style.SUCCESS('开始初始化官方模板和默认用户...'))

        # 1. 检查并创建 id=1 的 admin 用户
        admin_user = self._ensure_admin_user(skip_admin)
        if not admin_user:
            return

        # 2. 创建官方账户模板
        self._create_official_account_template(admin_user, force)

        # 3. 应用官方账户模板到 admin 用户
        self._apply_account_templates_to_admin(admin_user)

        # 4. 创建官方映射模板
        self._create_official_mapping_templates(admin_user, force)

        # 5. 应用官方映射模板到 admin 用户
        self._apply_mapping_templates_to_admin(admin_user)

        # 6. 确保 admin 用户有格式化配置
        self._ensure_format_config(admin_user)

        self.stdout.write(self.style.SUCCESS('✓ 官方模板和默认用户初始化完成'))

    def _ensure_admin_user(self, skip_admin):
        """确保 id=1 的 admin 用户存在"""
        try:
            admin_user = User.objects.get(id=1)
            self.stdout.write(self.style.SUCCESS(f'✓ 默认用户已存在: {admin_user.username}'))
            return admin_user
        except User.DoesNotExist:
            if skip_admin:
                self.stdout.write(self.style.WARNING('默认用户（ID=1）不存在，且设置了 --skip-admin'))
                return None

            # 创建 admin 用户
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123456'
            )
            # 确保 ID 为 1
            if admin_user.id != 1:
                self.stdout.write(self.style.WARNING(f'创建的用户 ID={admin_user.id}，不是预期的 ID=1'))

            self.stdout.write(self.style.SUCCESS(f'✓ 创建默认用户: {admin_user.username} (ID={admin_user.id})'))
            return admin_user

    def _create_official_account_template(self, admin_user, force):
        """创建官方账户模板"""
        template_name = "中国用户标准账户模板"

        # 检查模板是否已存在
        existing_template = AccountTemplate.objects.filter(
            name=template_name, 
            is_official=True
        ).first()

        if existing_template:
            if force:
                existing_template.delete()
                self.stdout.write(self.style.WARNING(f'删除现有官方模板: {template_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'官方账户模板已存在: {template_name}，使用 --force 强制重建'))
                return

        # 创建模板
        with transaction.atomic():
            template = AccountTemplate.objects.create(
                name=template_name,
                description="适用于中国用户的标准 Beancount 账户结构",
                is_public=True,
                is_official=True,
                version="1.0.0",
                owner=admin_user
            )

            # 标准账户结构（基于现有项目的实际使用）
            standard_accounts = [
                # 资产账户 - 网络支付
                'Assets:Savings:Web:AliPay',
                'Assets:Savings:Web:AliFund',
                'Assets:Savings:Web:WechatPay',
                'Assets:Savings:Web:WechatFund',
                'Assets:Savings:Web:XiaoHeBao',

                # 资产账户 - 银行储蓄卡
                'Assets:Savings:Bank:CMB',
                'Assets:Savings:Bank:ICBC',
                'Assets:Savings:Bank:CCB',
                'Assets:Savings:Bank:BOC',
                'Assets:Savings:Bank:ABC',
                'Assets:Savings:Bank:NBCB',
                'Assets:Savings:Bank:HXB',
                'Assets:Savings:Bank:ZJRCUB',
                'Assets:Savings:Bank:CEB',

                # 资产账户 - 储值账户
                'Assets:Savings:Recharge',
                'Assets:Savings:Recharge:Operator',

                # 资产账户 - 应收账款
                'Assets:Receivables:Personal',

                # 资产账户 - 其他
                'Assets:Other',

                # 负债账户 - 信用卡（银行）
                'Liabilities:CreditCard:Bank:CMB',
                'Liabilities:CreditCard:Bank:ICBC',
                'Liabilities:CreditCard:Bank:CCB',
                'Liabilities:CreditCard:Bank:CITIC',

                # 负债账户 - 信用卡（网络）
                'Liabilities:CreditCard:Web:HuaBei',
                'Liabilities:CreditCard:Web:DouYin',

                # 负债账户 - 应付账款
                'Liabilities:Payables:Personal',

                # 权益账户
                'Equity:OpenBalance',
                'Equity:Adjustments',

                # 收入账户 - 主动收入
                'Income:Active:Salary',
                'Income:Active:Bonus',

                # 收入账户 - 投资收入
                'Income:Investment:Dividends',
                'Income:Investment:Interest',

                # 收入账户 - 副业收入
                'Income:Sideline',
                'Income:Sideline:DiDi',

                # 收入账户 - 业务收入
                'Income:Business',

                # 收入账户 - 应收账款
                'Income:Receivables:RedPacket',
                'Income:Receivables:Transfer',

                # 收入账户 - 优惠折扣
                'Income:Discount',

                # 收入账户 - 其他
                'Income:Other',

                # 支出账户 - 餐饮
                'Expenses:Food',
                'Expenses:Food:Breakfast',
                'Expenses:Food:Lunch',
                'Expenses:Food:Dinner',
                'Expenses:Food:DrinkFruit',

                # 支出账户 - 交通
                'Expenses:TransPort:Public',
                'Expenses:TransPort:Private',
                'Expenses:TransPort:Private:Fuel',
                'Expenses:TransPort:Private:Park',

                # 支出账户 - 购物
                'Expenses:Shopping',
                'Expenses:Shopping:Digital',
                'Expenses:Shopping:Clothing',
                'Expenses:Shopping:Makeup',
                'Expenses:Shopping:Parent',

                # 支出账户 - 医疗健康
                'Expenses:Health:Medical',
                'Expenses:Health:Outpatient',

                # 支出账户 - 文化娱乐
                'Expenses:Culture',
                'Expenses:Culture:Entertainment',
                'Expenses:Culture:Subscription',

                # 支出账户 - 家居生活
                'Expenses:Home',
                'Expenses:Home:Recharge',
                'Expenses:Home:Daily',
                'Expenses:Home:Decoration',

                # 支出账户 - 金融
                'Expenses:Finance:Commission',
                'Expenses:Finance:Insurance',

                # 支出账户 - 政府
                'Expenses:Government',
                'Expenses:Government:Fine',

                # 支出账户 - 其他
                'Expenses:Other',
            ]

            # 创建模板项
            for account_path in standard_accounts:
                AccountTemplateItem.objects.create(
                    template=template,
                    account_path=account_path,
                    enable=True
                )

            self.stdout.write(self.style.SUCCESS(
                f'✓ 创建官方账户模板: {template_name} ({len(standard_accounts)} 个账户)'
            ))

    def _apply_account_templates_to_admin(self, admin_user):
        """应用账户模板到 admin 用户"""
        from project.apps.account.signals import apply_official_account_templates

        # 检查是否已有账户
        existing_count = Account.objects.filter(owner=admin_user).count()
        if existing_count > 0:
            self.stdout.write(self.style.WARNING(
                f'admin 用户已有 {existing_count} 个账户，跳过自动应用'
            ))
            return

        apply_official_account_templates(admin_user)
        final_count = Account.objects.filter(owner=admin_user).count()
        self.stdout.write(self.style.SUCCESS(
            f'✓ 为 admin 用户创建了 {final_count} 个账户'
        ))

    def _ensure_format_config(self, admin_user):
        """确保 admin 用户有格式化配置"""
        config, created = FormatConfig.objects.get_or_create(
            owner=admin_user,
            defaults={
                'flag': '*',
                'show_note': True,
                'show_tag': True,
                'show_time': True,
                'show_uuid': True,
                'show_status': True,
                'show_discount': True,
                'income_template': 'Income:Discount',
                'commission_template': 'Expenses:Finance:Commission',
                'currency': 'CNY',
                'ai_model': 'BERT'
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('✓ 创建 admin 用户的格式化配置'))
        else:
            self.stdout.write(self.style.SUCCESS('✓ admin 用户的格式化配置已存在'))

    def _create_official_mapping_templates(self, admin_user, force):
        """创建官方映射模板"""
        from project.apps.account.models import Account

        # 检查现有官方映射模板
        expense_template = Template.objects.filter(name='官方支出映射', is_official=True).first()
        income_template = Template.objects.filter(name='官方收入映射', is_official=True).first()
        assets_template = Template.objects.filter(name='官方资产映射', is_official=True).first()

        # 支出映射模板
        if not expense_template or force:
            if expense_template and force:
                expense_template.delete()

            expense_template = Template.objects.create(
                name='官方支出映射',
                description='中国用户常用支出映射',
                type='expense',
                is_public=True,
                is_official=True,
                version='1.0.0',
                owner=admin_user
            )

            # 获取对应的账户对象
            expense_mappings = [
                # 格式: (key, payee, account_path, currency)
                ('蜜雪冰城', '蜜雪冰城', 'Expenses:Food:DrinkFruit', 'CNY'),
                ('古茗', '古茗', 'Expenses:Food:DrinkFruit', 'CNY'),
                ('喜茶', '喜茶', 'Expenses:Food:DrinkFruit', 'CNY'),
                ('茶百道', '茶百道', 'Expenses:Food:DrinkFruit', 'CNY'),
                ('一点点', '一点点', 'Expenses:Food:DrinkFruit', 'CNY'),
                ('霸王茶姬', '霸王茶姬', 'Expenses:Food:DrinkFruit', 'CNY'),
                ('新时沏', '新时沏', 'Expenses:Food:DrinkFruit', 'CNY'),
                ('luckin', '瑞幸', 'Expenses:Food:DrinkFruit', 'CNY'),
                ('肯德基', '肯德基', 'Expenses:Food', 'CNY'),
                ('华莱士', '华莱士', 'Expenses:Food', 'CNY'),
                ('塔斯汀', '塔斯汀', 'Expenses:Food', 'CNY'),
                ('十足', '十足', 'Expenses:Food', 'CNY'),
                ('饿了么', '饿了么', 'Expenses:Food', 'CNY'),
                ('美团平台商户', '美团', 'Expenses:Food', 'CNY'),
                ('美团订单', '美团', 'Expenses:Food', 'CNY'),
                ('停车', '', 'Expenses:TransPort:Private:Park', 'CNY'),
                ('充电', '', 'Expenses:TransPort:Private:Fuel', 'CNY'),
                ('加油', '', 'Expenses:TransPort:Private:Fuel', 'CNY'),
                ('中国石油', '中国石油', 'Expenses:TransPort:Private:Fuel', 'CNY'),
                ('ETC', '', 'Expenses:TransPort:Public', 'CNY'),
                ('地铁', '', 'Expenses:TransPort:Public', 'CNY'),
                ('12306', '12306', 'Expenses:TransPort:Public', 'CNY'),
                ('淘宝', '淘宝', 'Expenses:Shopping', 'CNY'),
                ('京东', '京东', 'Expenses:Shopping', 'CNY'),
                ('拼多多', '拼多多', 'Expenses:Shopping', 'CNY'),
                ('得物', '得物', 'Expenses:Shopping:Clothing', 'CNY'),
                ('药房', '', 'Expenses:Health:Medical', 'CNY'),
                ('药店', '', 'Expenses:Health:Medical', 'CNY'),
                ('医院', '', 'Expenses:Health:Outpatient', 'CNY'),
                ('超市', '', 'Expenses:Shopping', 'CNY'),
            ]

            for key, payee, account_path, currency in expense_mappings:
                account_obj = Account.objects.filter(account=account_path, owner=admin_user).first()
                if account_obj:
                    TemplateItem.objects.create(
                        template=expense_template,
                        key=key,
                        payee=payee if payee else None,
                        account=account_obj,
                        currency=currency
                    )

            self.stdout.write(self.style.SUCCESS(
                f'✓ 创建官方支出映射模板 ({len(expense_mappings)} 项)'
            ))

        # 资产映射模板
        if not assets_template or force:
            if assets_template and force:
                assets_template.delete()

            assets_template = Template.objects.create(
                name='官方资产映射',
                description='中国用户常用资产映射',
                type='assets',
                is_public=True,
                is_official=True,
                version='1.0.0',
                owner=admin_user
            )

            assets_mappings = [
                # 格式: (key, full, account_path)
                ('余额', '支付宝余额', 'Assets:Savings:Web:AliPay'),
                ('账户余额', '支付宝余额', 'Assets:Savings:Web:AliPay'),
                ('余额宝', '支付宝余额宝', 'Assets:Savings:Web:AliFund'),
                ('花呗', '支付宝花呗', 'Liabilities:CreditCard:Web:HuaBei'),
                ('零钱', '微信零钱', 'Assets:Savings:Web:WechatPay'),
                ('零钱通', '微信零钱通', 'Assets:Savings:Web:WechatFund'),
                ('/', '微信零钱', 'Assets:Savings:Web:WechatPay'),
            ]

            for key, full, account_path in assets_mappings:
                account_obj = Account.objects.filter(account=account_path, owner=admin_user).first()
                if account_obj:
                    TemplateItem.objects.create(
                        template=assets_template,
                        key=key,
                        full=full,
                        account=account_obj
                    )

            self.stdout.write(self.style.SUCCESS(
                f'✓ 创建官方资产映射模板 ({len(assets_mappings)} 项)'
            ))

        # 收入映射模板
        if not income_template or force:
            if income_template and force:
                income_template.delete()

            income_template = Template.objects.create(
                name='官方收入映射',
                description='中国用户常用收入映射',
                type='income',
                is_public=True,
                is_official=True,
                version='1.0.0',
                owner=admin_user
            )

            income_mappings = [
                # 格式: (key, payer, account_path)
                ('红包', None, 'Income:Receivables:RedPacket'),
                ('小荷包', None, 'Assets:Savings:Web:XiaoHeBao'),
            ]

            for key, payer, account_path in income_mappings:
                account_obj = Account.objects.filter(account=account_path, owner=admin_user).first()
                if account_obj:
                    TemplateItem.objects.create(
                        template=income_template,
                        key=key,
                        payer=payer,
                        account=account_obj
                    )

            self.stdout.write(self.style.SUCCESS(
                f'✓ 创建官方收入映射模板 ({len(income_mappings)} 项)'
            ))

    def _apply_mapping_templates_to_admin(self, admin_user):
        """应用映射模板到 admin 用户"""
        from project.apps.maps.signals import apply_official_templates
        from project.apps.maps.models import Expense, Assets, Income

        # 检查是否已有映射
        existing_expenses = Expense.objects.filter(owner=admin_user).count()
        existing_assets = Assets.objects.filter(owner=admin_user).count()
        existing_incomes = Income.objects.filter(owner=admin_user).count()
        total_existing = existing_expenses + existing_assets + existing_incomes

        if total_existing > 0:
            self.stdout.write(self.style.WARNING(
                f'admin 用户已有 {total_existing} 个映射，跳过自动应用'
            ))
            return

        apply_official_templates(admin_user)

        final_expenses = Expense.objects.filter(owner=admin_user).count()
        final_assets = Assets.objects.filter(owner=admin_user).count()
        final_incomes = Income.objects.filter(owner=admin_user).count()

        self.stdout.write(self.style.SUCCESS(
            f'✓ 为 admin 用户创建映射: 支出={final_expenses}, 资产={final_assets}, 收入={final_incomes}'
        ))

