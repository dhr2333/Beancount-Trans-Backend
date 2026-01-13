# project/apps/account/management/commands/apply_templates_to_users.py
"""
批量为用户应用官方账户模板和映射模板

使用方法:
    python manage.py apply_templates_to_users --all-users  # 为所有用户应用
    python manage.py apply_templates_to_users --user-ids 1,2,3  # 为指定用户应用
    python manage.py apply_templates_to_users --all-users --dry-run  # 预览模式
    python manage.py apply_templates_to_users --all-users --force  # 强制覆盖现有数据
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from project.apps.account.models import Account, AccountTemplate, AccountTemplateItem
from project.apps.maps.models import Template, TemplateItem, Expense, Assets, Income
from project.apps.translate.models import FormatConfig

User = get_user_model()


class Command(BaseCommand):
    help = '批量为用户应用官方账户模板和映射模板'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all-users',
            action='store_true',
            help='为所有用户应用官方模板',
        )
        parser.add_argument(
            '--user-ids',
            type=str,
            help='指定用户ID列表，用逗号分隔，例如: 1,2,3',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='预览模式，不实际创建数据',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制模式，删除用户现有的账户和映射后重新创建',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='跳过已有账户或映射的用户',
        )

    def handle(self, *args, **options):
        all_users = options.get('all_users', False)
        user_ids_str = options.get('user_ids')
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)
        skip_existing = options.get('skip_existing', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 预览模式：不会实际创建数据'))

        if force and skip_existing:
            self.stdout.write(self.style.ERROR('❌ --force 和 --skip-existing 不能同时使用'))
            return

        # 确定目标用户列表
        target_users = self._get_target_users(all_users, user_ids_str)
        if not target_users:
            self.stdout.write(self.style.ERROR('❌ 没有找到目标用户'))
            return

        self.stdout.write(self.style.SUCCESS(f'\n目标用户数量: {len(target_users)}'))

        # 获取官方模板
        official_templates = self._get_official_templates()
        if not official_templates['account_template']:
            self.stdout.write(self.style.ERROR('❌ 未找到官方账户模板，请先运行: python manage.py init_official_templates'))
            return

        # 统计信息
        stats = {
            'total_users': len(target_users),
            'processed_users': 0,
            'skipped_users': 0,
            'failed_users': 0,
            'created_accounts': 0,
            'created_expenses': 0,
            'created_assets': 0,
            'created_incomes': 0,
            'created_configs': 0,
        }

        # 为每个用户应用模板
        for user in target_users:
            self.stdout.write(self.style.HTTP_INFO(f'\n处理用户: {user.username} (ID={user.id})'))

            try:
                result = self._apply_templates_to_user(
                    user, 
                    official_templates, 
                    dry_run=dry_run, 
                    force=force,
                    skip_existing=skip_existing
                )

                if result['skipped']:
                    stats['skipped_users'] += 1
                    self.stdout.write(self.style.WARNING(f'⏭️  跳过用户 {user.username}（{result["reason"]}）'))
                else:
                    stats['processed_users'] += 1
                    stats['created_accounts'] += result['accounts']
                    stats['created_expenses'] += result['expenses']
                    stats['created_assets'] += result['assets']
                    stats['created_incomes'] += result['incomes']
                    stats['created_configs'] += result['configs']
                    self.stdout.write(self.style.SUCCESS(
                        f'✓ 完成 {user.username}: '
                        f'账户={result["accounts"]}, '
                        f'支出={result["expenses"]}, '
                        f'资产={result["assets"]}, '
                        f'收入={result["incomes"]}'
                    ))

            except Exception as e:
                stats['failed_users'] += 1
                self.stdout.write(self.style.ERROR(f'❌ 处理用户 {user.username} 失败: {str(e)}'))
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))

        # 输出统计信息
        self._print_summary(stats, dry_run)

    def _get_target_users(self, all_users, user_ids_str):
        """获取目标用户列表"""
        if all_users:
            return User.objects.all().order_by('id')
        elif user_ids_str:
            user_ids = [int(uid.strip()) for uid in user_ids_str.split(',')]
            return User.objects.filter(id__in=user_ids).order_by('id')
        else:
            self.stdout.write(self.style.ERROR('请指定 --all-users 或 --user-ids'))
            return []

    def _get_official_templates(self):
        """获取官方模板"""
        account_template = AccountTemplate.objects.filter(is_official=True).first()
        expense_template = Template.objects.filter(type='expense', is_official=True).first()
        income_template = Template.objects.filter(type='income', is_official=True).first()
        assets_template = Template.objects.filter(type='assets', is_official=True).first()

        return {
            'account_template': account_template,
            'expense_template': expense_template,
            'income_template': income_template,
            'assets_template': assets_template,
        }

    def _apply_templates_to_user(self, user, official_templates, dry_run=False, force=False, skip_existing=False):
        """为单个用户应用模板"""
        result = {
            'skipped': False,
            'reason': '',
            'accounts': 0,
            'expenses': 0,
            'assets': 0,
            'incomes': 0,
            'configs': 0,
        }

        # 检查用户是否已有数据
        existing_accounts = Account.objects.filter(owner=user).count()
        existing_expenses = Expense.objects.filter(owner=user).count()
        existing_assets = Assets.objects.filter(owner=user).count()
        existing_incomes = Income.objects.filter(owner=user).count()
        has_existing_data = existing_accounts > 0 or existing_expenses > 0 or existing_assets > 0 or existing_incomes > 0

        if has_existing_data:
            if skip_existing:
                result['skipped'] = True
                result['reason'] = f'已有数据（账户={existing_accounts}, 映射={existing_expenses+existing_assets+existing_incomes}）'
                return result
            elif force:
                if not dry_run:
                    # 删除现有数据
                    Account.objects.filter(owner=user).delete()
                    Expense.objects.filter(owner=user).delete()
                    Assets.objects.filter(owner=user).delete()
                    Income.objects.filter(owner=user).delete()
                    self.stdout.write(self.style.WARNING(f'  🗑️  已删除用户 {user.username} 的现有数据'))

        if dry_run:
            # 预览模式：只统计将要创建的数量
            if official_templates['account_template']:
                result['accounts'] = official_templates['account_template'].items.count()
            if official_templates['expense_template']:
                result['expenses'] = official_templates['expense_template'].items.count()
            if official_templates['income_template']:
                result['incomes'] = official_templates['income_template'].items.count()
            if official_templates['assets_template']:
                result['assets'] = official_templates['assets_template'].items.count()
            if not FormatConfig.objects.filter(owner=user).exists():
                result['configs'] = 1
            return result

        # 实际创建数据（使用事务）
        with transaction.atomic():
            # 1. 应用账户模板
            if official_templates['account_template']:
                created_accounts = self._create_accounts_from_template(user, official_templates['account_template'])
                result['accounts'] = len(created_accounts)

            # 2. 应用映射模板
            if official_templates['expense_template']:
                result['expenses'] = self._create_expense_mappings(user, official_templates['expense_template'])

            if official_templates['income_template']:
                result['incomes'] = self._create_income_mappings(user, official_templates['income_template'])

            if official_templates['assets_template']:
                result['assets'] = self._create_assets_mappings(user, official_templates['assets_template'])

            # 3. 创建格式化配置
            if not FormatConfig.objects.filter(owner=user).exists():
                FormatConfig.objects.create(
                    owner=user,
                    flag='*',
                    show_note=True,
                    show_tag=True,
                    show_time=True,
                    show_uuid=True,
                    show_status=True,
                    show_discount=True,
                    income_template='Income:Discount',
                    commission_template='Expenses:Finance:Commission',
                    currency='CNY',
                    ai_model='BERT'
                )
                result['configs'] = 1

        return result

    def _create_accounts_from_template(self, user, account_template):
        """从账户模板创建账户"""
        created_accounts = {}
        template_items = account_template.items.all().order_by('account_path')

        for item in template_items:
            account_path = item.account_path

            # 跳过已存在的账户
            if Account.objects.filter(owner=user, account=account_path).exists():
                existing = Account.objects.get(owner=user, account=account_path)
                created_accounts[account_path] = existing
                continue

            # 查找或创建父账户
            parent_account = None
            if ':' in account_path:
                parent_path = ':'.join(account_path.split(':')[:-1])
                if parent_path in created_accounts:
                    parent_account = created_accounts[parent_path]
                else:
                    parent_account = Account.objects.filter(owner=user, account=parent_path).first()

            # 创建账户
            account = Account.objects.create(
                owner=user,
                account=account_path,
                parent=parent_account,
                enable=item.enable
            )
            created_accounts[account_path] = account

        return created_accounts

    def _create_expense_mappings(self, user, expense_template):
        """创建支出映射"""
        created_count = 0
        template_items = expense_template.items.all()

        for item in template_items:
            # 检查账户是否存在
            # item.account 现在是账户路径字符串，不再是账户对象
            if item.account:
                account = Account.objects.filter(owner=user, account=item.account).first()
                if not account:
                    continue  # 跳过账户不存在的映射
            else:
                account = None

            # 创建映射
            Expense.objects.create(
                owner=user,
                key=item.key,
                payee=item.payee,
                expend=account,
                currency=item.currency,
                enable=True
            )
            created_count += 1

        return created_count

    def _create_income_mappings(self, user, income_template):
        """创建收入映射"""
        created_count = 0
        template_items = income_template.items.all()

        for item in template_items:
            # 检查账户是否存在
            # item.account 现在是账户路径字符串，不再是账户对象
            if item.account:
                account = Account.objects.filter(owner=user, account=item.account).first()
                if not account:
                    continue
            else:
                account = None

            # 创建映射
            Income.objects.create(
                owner=user,
                key=item.key,
                payer=item.payer,
                income=account,
                enable=True
            )
            created_count += 1

        return created_count

    def _create_assets_mappings(self, user, assets_template):
        """创建资产映射"""
        created_count = 0
        template_items = assets_template.items.all()

        for item in template_items:
            # 检查账户是否存在
            # item.account 现在是账户路径字符串，不再是账户对象
            if item.account:
                account = Account.objects.filter(owner=user, account=item.account).first()
                if not account:
                    continue
            else:
                account = None

            # 创建映射
            Assets.objects.create(
                owner=user,
                key=item.key,
                full=item.full,
                assets=account,
                enable=True
            )
            created_count += 1

        return created_count

    def _print_summary(self, stats, dry_run):
        """输出统计摘要"""
        self.stdout.write('\n' + '=' * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING('📊 预览统计（未实际创建）'))
        else:
            self.stdout.write(self.style.SUCCESS('📊 执行统计'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'总用户数:     {stats["total_users"]}')
        self.stdout.write(f'已处理用户:   {stats["processed_users"]}')
        self.stdout.write(f'跳过用户:     {stats["skipped_users"]}')
        self.stdout.write(f'失败用户:     {stats["failed_users"]}')
        self.stdout.write('-' * 60)
        self.stdout.write(f'创建账户数:   {stats["created_accounts"]}')
        self.stdout.write(f'创建支出映射: {stats["created_expenses"]}')
        self.stdout.write(f'创建资产映射: {stats["created_assets"]}')
        self.stdout.write(f'创建收入映射: {stats["created_incomes"]}')
        self.stdout.write(f'创建配置:     {stats["created_configs"]}')
        self.stdout.write('=' * 60)

        if dry_run:
            self.stdout.write(self.style.WARNING('\n💡 这是预览模式，要实际执行请去掉 --dry-run 参数'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ 批量应用完成！'))


