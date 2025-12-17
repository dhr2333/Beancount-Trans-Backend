# project/apps/file_manager/management/commands/migrate_to_trans_structure.py
"""
数据迁移脚本：将现有用户的解析结果移动到trans目录

迁移逻辑：
1. 遍历所有用户目录
2. 查找根目录下的 .bean 文件（排除main.bean）
3. 移动到 trans/ 目录
4. 更新main.bean中的include路径（移除旧的include，确保包含 include "trans/main.bean"）
5. 为每个迁移的文件添加到trans/main.bean的include
"""
import os
import shutil
import re
from pathlib import Path
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
from project.utils.file import BeanFileManager

User = get_user_model()


class Command(BaseCommand):
    help = '将现有用户的解析结果移动到trans目录，更新main.bean和trans/main.bean'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示将要执行的操作，不实际执行',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='仅迁移指定用户（用户名）',
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            help='迁移前备份用户目录',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        user_filter = options.get('user')
        backup = options['backup']

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

        total_users = 0
        total_files = 0
        total_errors = 0

        for user in users:
            try:
                migrated_count = self.migrate_user(user, dry_run, backup)
                if migrated_count > 0:
                    total_users += 1
                    total_files += migrated_count
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ 用户 {user.username}: 迁移了 {migrated_count} 个文件'
                        )
                    )
            except Exception as e:
                total_errors += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ 用户 {user.username}: 迁移失败 - {str(e)}')
                )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== 迁移完成 ==='))
        self.stdout.write(f'成功迁移用户数: {total_users}')
        self.stdout.write(f'迁移文件总数: {total_files}')
        if total_errors > 0:
            self.stdout.write(self.style.ERROR(f'失败用户数: {total_errors}'))

    def migrate_user(self, user, dry_run=False, backup=False):
        """迁移单个用户的文件"""
        user_assets_path = Path(BeanFileManager.get_user_assets_path(user.username))

        if not user_assets_path.exists():
            return 0

        # 备份（如果需要）
        if backup and not dry_run:
            backup_path = user_assets_path.parent / f"{user.username}_backup"
            if backup_path.exists():
                shutil.rmtree(backup_path)
            shutil.copytree(user_assets_path, backup_path)
            self.stdout.write(f'  备份到: {backup_path}')

        # 1. 查找根目录下的 .bean 文件（排除main.bean）
        bean_files = []
        for bean_file in user_assets_path.glob('*.bean'):
            if bean_file.name != 'main.bean':
                bean_files.append(bean_file)

        if not bean_files:
            return 0

        # 2. 创建trans目录
        trans_dir = user_assets_path / 'trans'
        if not dry_run:
            trans_dir.mkdir(exist_ok=True)

        # 3. 移动文件到trans目录
        migrated_files = []
        for bean_file in bean_files:
            target_path = trans_dir / bean_file.name
            if not dry_run:
                shutil.move(str(bean_file), str(target_path))
            migrated_files.append(bean_file.name)
            self.stdout.write(f'  移动: {bean_file.name} -> trans/{bean_file.name}')

        # 4. 更新main.bean
        main_bean_path = user_assets_path / 'main.bean'
        if main_bean_path.exists():
            self.update_main_bean(main_bean_path, migrated_files, dry_run)
        else:
            # 如果main.bean不存在，创建新的
            if not dry_run:
                BeanFileManager.update_main_bean_include(user.username, '', 'add')
            self.stdout.write('  创建新的 main.bean')

        # 5. 更新trans/main.bean（为每个迁移的文件添加include）
        if not dry_run:
            for bean_filename in migrated_files:
                BeanFileManager.update_trans_main_bean_include(
                    user.username, bean_filename, action='add'
                )
        else:
            self.stdout.write(f'  将在 trans/main.bean 中添加 {len(migrated_files)} 个 include')

        return len(migrated_files)

    def update_main_bean(self, main_bean_path, migrated_files, dry_run=False):
        """更新main.bean文件"""
        with open(main_bean_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        removed_includes = []

        # 构建需要移除的include模式
        patterns_to_remove = []
        for bean_filename in migrated_files:
            # 匹配 include "filename.bean" 或 include "trans/filename.bean"
            pattern = re.compile(rf'^\s*include\s*"(?:trans/)?{re.escape(bean_filename)}"\s*$')
            patterns_to_remove.append((pattern, bean_filename))

        # 处理每一行
        for line in lines:
            should_remove = False
            for pattern, filename in patterns_to_remove:
                if pattern.match(line):
                    should_remove = True
                    removed_includes.append(filename)
                    break
            if not should_remove:
                new_lines.append(line)

        # 检查是否包含 include "trans/main.bean"
        trans_main_pattern = re.compile(r'^\s*include\s*"trans/main\.bean"\s*$', re.MULTILINE)
        has_trans_main = any(trans_main_pattern.match(line) for line in new_lines)

        # 如果不存在，添加到文件末尾
        if not has_trans_main:
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines[-1] += '\n'
            new_lines.append('include "trans/main.bean"\n')

        # 写入更新后的内容
        if not dry_run:
            with open(main_bean_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

        if removed_includes:
            self.stdout.write(f'  从 main.bean 中移除了 {len(removed_includes)} 个旧的 include')
        if not has_trans_main:
            self.stdout.write('  在 main.bean 中添加了 include "trans/main.bean"')

