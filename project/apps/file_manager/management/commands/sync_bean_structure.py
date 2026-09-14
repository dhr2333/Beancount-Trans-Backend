# project/apps/file_manager/management/commands/sync_bean_structure.py
"""
存量用户账本结构对齐脚本：将用户已存在的 .bean 文件对齐到平台目录结构。

对齐逻辑：
1. trans/ 下的 .bean 文件需要镜像文件管理中的目录结构：
   即文件管理目录 "Test/202608_alipay.csv" 对应账本 "Test/202608_alipay.bean"。
2. 遍历用户的每个 File 记录，计算其在 trans/ 下应有的目标相对路径
   （file.get_bean_relative_path()）。
3. 如果目标位置的 .bean 已存在，说明已对齐，仅确保 trans/main.bean 中的
   include 存在即可。
4. 否则在 trans/ 目录下（含子目录）查找同名的 .bean 文件：
   - 找到唯一候选时，将其从当前位置移动到目标相对路径；
   - 存在多个候选时，优先选择位于 trans/ 根目录的那个，并输出歧义警告；
   - 找不到候选时跳过（不为缺失的账本创建 include）。
5. 移动完成后确保 trans/main.bean 中存在对应的 include（幂等）。

幂等性（Idempotency）：
- 首次运行后，所有 .bean 均已位于目标相对路径，第二次运行时目标已存在，
  直接计入 "已对齐"，不会再次移动文件；
- add_bean_to_trans_main 会去重 include 行，重复调用不会产生重复 include；
- 因此脚本可安全地重复执行，第二次运行不会对磁盘或 trans/main.bean 造成任何改动。
"""
import os
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from project.apps.file_manager.models import File
from project.utils.file import BeanFileManager

User = get_user_model()


class Command(BaseCommand):
    help = '将存量用户账本 .bean 文件对齐到平台目录结构（trans/ 子目录镜像文件管理目录）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示即将执行的移动计划，不实际修改磁盘或 trans/main.bean',
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

        total_migrated = 0
        total_aligned = 0
        total_skipped = 0
        total_errors = 0

        for user in users:
            try:
                stats = self.sync_user(user, dry_run)
            except Exception as e:
                total_errors += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ 用户 {user.username}: 对齐失败 - {str(e)}')
                )
                continue

            total_migrated += stats['migrated']
            total_aligned += stats['aligned']
            total_skipped += stats['skipped']
            total_errors += stats['errors']

            self.stdout.write(
                f'用户 {user.username}: 迁移 {stats["migrated"]} 个, '
                f'已对齐 {stats["aligned"]} 个, '
                f'跳过 {stats["skipped"]} 个, 错误 {stats["errors"]} 个'
            )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== 同步完成 ==='))
        self.stdout.write(f'迁移文件数: {total_migrated}')
        self.stdout.write(f'已对齐文件数: {total_aligned}')
        self.stdout.write(f'跳过文件数: {total_skipped}')
        if total_errors > 0:
            self.stdout.write(self.style.ERROR(f'错误数: {total_errors}'))

    def sync_user(self, user, dry_run=False):
        """对齐单个用户的 .bean 文件结构

        Args:
            user: User 实例
            dry_run: 为 True 时仅打印计划，不修改磁盘与 trans/main.bean

        Returns:
            dict: {'migrated': int, 'aligned': int, 'skipped': int, 'errors': int}
        """
        stats = {'migrated': 0, 'aligned': 0, 'skipped': 0, 'errors': 0}

        trans_dir = BeanFileManager._resolve_trans_path(user, '')
        trans_root = os.path.abspath(trans_dir)

        for file in File.objects.filter(owner=user):
            target_rel = file.get_bean_relative_path()
            target_abs = BeanFileManager._resolve_trans_path(user, target_rel)

            # 目标位置已存在 -> 已对齐，仅确保 include 存在（幂等）
            if os.path.exists(target_abs):
                if not dry_run:
                    BeanFileManager.add_bean_to_trans_main(user, target_rel)
                stats['aligned'] += 1
                continue

            # 在 trans/ 目录下（含子目录）查找同名的 .bean 文件
            base_name = os.path.splitext(file.name)[0]
            target_real = os.path.realpath(target_abs)
            candidates = [
                p for p in Path(trans_dir).rglob(f'{base_name}.bean')
                if os.path.realpath(str(p)) != target_real
            ]

            if not candidates:
                self.stdout.write(
                    self.style.WARNING(
                        f'  未找到对应 .bean，跳过: {target_rel}'
                    )
                )
                stats['skipped'] += 1
                continue

            if len(candidates) > 1:
                self.stdout.write(
                    self.style.WARNING(
                        f'  发现 {len(candidates)} 个同名 .bean，存在歧义，'
                        f'将优先选择 trans/ 根目录下的文件: {target_rel}'
                    )
                )

            # 优先选择位于 trans/ 根目录的候选，否则取第一个
            preferred = None
            for candidate in candidates:
                if os.path.dirname(os.path.abspath(str(candidate))) == trans_root:
                    preferred = candidate
                    break
            if preferred is None:
                preferred = candidates[0]

            old_rel = os.path.relpath(str(preferred), trans_dir).replace(os.sep, '/')

            if dry_run:
                self.stdout.write(f'  计划移动: {old_rel} -> {target_rel}')
                stats['migrated'] += 1
                continue

            try:
                BeanFileManager.move_bean_file(user, old_rel, target_rel)
            except FileExistsError:
                self.stdout.write(
                    self.style.ERROR(
                        f'  目标已存在，跳过以避免覆盖: {target_rel}'
                    )
                )
                stats['errors'] += 1
                continue

            # move_bean_file 已同步更新 include，此处为幂等的兜底操作
            BeanFileManager.add_bean_to_trans_main(user, target_rel)
            self.stdout.write(f'  移动: {old_rel} -> {target_rel}')
            stats['migrated'] += 1

        return stats
