# project/apps/file_manager/management/commands/ensure_collect_bean.py
"""
存量用户补齐 trans/collect.bean 系统账本脚本。

补齐逻辑：
1. 遍历所有用户（或用 --user 指定单个用户）。
2. 通过 os.path.exists(BeanFileManager.get_collect_bean_path(user)) 判断
   用户的 trans/collect.bean 是否已存在：
   - 不存在时计入 "新建"，调用 ensure_collect_bean 创建该文件（含注释头）；
   - 已存在时计入 "已存在"，仅确保 trans/main.bean 中存在对应的
     include "collect.bean"。
3. collect.bean 是平台维护的系统账本，用于承载非账单来源条目（账单来源条目
   仍写入各自的 trans/{账单名}.bean），因此需要为存量用户补齐。

幂等性（Idempotency）：
- ensure_collect_bean 不会覆盖已存在的 collect.bean 内容，重复调用不会
  改动文件；
- 其内部通过 add_bean_to_trans_main 添加 include，该方法自带去重逻辑，
  重复调用不会产生重复的 include 行；
- 因此脚本可安全地重复执行，第二次运行时所有用户均计入 "已存在"，
  不会对磁盘或 trans/main.bean 造成任何额外变更。
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from project.utils.file import BeanFileManager

User = get_user_model()


class Command(BaseCommand):
    help = '为存量用户补齐 trans/collect.bean 系统账本，并确保 trans/main.bean 包含对应 include'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示将要执行的操作，不修改磁盘与 trans/main.bean',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='仅处理指定用户（用户名）',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        user_filter = options.get('user')

        if dry_run:
            self.stdout.write(self.style.WARNING('=== 模拟运行模式（不会实际修改文件）==='))

        # 获取所有用户或指定用户
        if user_filter:
            try:
                users = [User.objects.get(username=user_filter)]
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'用户 {user_filter} 不存在'))
                return
        else:
            users = User.objects.all()

        total_created = 0
        total_existing = 0
        total_errors = 0

        for user in users:
            try:
                stats = self.ensure_user(user, dry_run)
            except Exception as e:
                total_errors += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ 用户 {user.username}: 补齐失败 - {str(e)}')
                )
                continue

            total_created += stats['created']
            total_existing += stats['existing']

            self.stdout.write(
                f'用户 {user.username}: 新建 {stats["created"]} 个, '
                f'已存在 {stats["existing"]} 个, 错误 {stats["errors"]} 个'
            )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== 补齐完成 ==='))
        self.stdout.write(f'新建文件数: {total_created}')
        self.stdout.write(f'已存在文件数: {total_existing}')
        if total_errors > 0:
            self.stdout.write(self.style.ERROR(f'错误数: {total_errors}'))

    def ensure_user(self, user, dry_run=False):
        """为单个用户补齐 trans/collect.bean

        Args:
            user: User 实例
            dry_run: 为 True 时仅打印计划，不修改磁盘与 trans/main.bean

        Returns:
            dict: {'created': int, 'existing': int, 'errors': int}
        """
        stats = {'created': 0, 'existing': 0, 'errors': 0}

        collect_bean_path = BeanFileManager.get_collect_bean_path(user)

        if os.path.exists(collect_bean_path):
            # 文件已存在 -> 仅确保 include 存在（幂等）
            stats['existing'] += 1
            if dry_run:
                self.stdout.write('  collect.bean 已存在，计划确保 include "collect.bean"')
                return stats

            BeanFileManager.ensure_collect_bean(user)
            self.stdout.write('  collect.bean 已存在，已确保 include "collect.bean"')
            return stats

        # 文件不存在 -> 新建
        stats['created'] += 1
        if dry_run:
            self.stdout.write(f'  计划创建: {collect_bean_path}')
            return stats

        BeanFileManager.ensure_collect_bean(user)
        self.stdout.write(f'  创建: {collect_bean_path}')

        return stats
