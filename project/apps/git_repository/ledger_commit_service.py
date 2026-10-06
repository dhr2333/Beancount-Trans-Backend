"""trans/ 条目迁移到月度账本的提交服务

用于 Git 用户把 trans/ 下已审核的条目按交易日期归入仓库根的月度文件
（{year}/{MM}.bean），提交并推送到远程，使其可通过 git pull 取回。
"""
import logging
import os
from typing import Any, Dict, List

from project.utils.file import BeanFileManager
from .services import PlatformGitService, GitServiceException

logger = logging.getLogger(__name__)


class LedgerCommitService:
    """trans/ → 月度账本迁移提交服务（全 classmethod）"""

    @classmethod
    def _collect_entries(cls, user) -> Dict[str, Any]:
        """扫描 trans/ 下全部 .bean（排除索引 main.bean），按 YYYY-MM 分桶收集条目"""
        buckets: Dict[str, List[str]] = {}
        files = BeanFileManager.iter_trans_bean_files(user, exclude_index=True)
        errors: List[Dict[str, str]] = []

        for rel_path in files:
            abs_path = BeanFileManager._resolve_trans_path(user, rel_path)
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except OSError as exc:
                errors.append({'file': rel_path, 'error': str(exc)})
                continue

            for date_key, block in BeanFileManager.split_entries(content):
                buckets.setdefault(date_key, []).append(block)

        return {'buckets': buckets, 'files': files, 'errors': errors}

    @classmethod
    def _existing_fingerprints(cls, user, year: int, month: int) -> set:
        """读取目标月度文件已有条目的指纹集合"""
        month_path = BeanFileManager.get_monthly_bean_path(user, year, month)
        if not os.path.exists(month_path):
            return set()
        with open(month_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            BeanFileManager._entry_fingerprint(block)
            for _date, block in BeanFileManager.split_entries(content)
        }

    @classmethod
    def _build_plan(cls, user, buckets: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """构建迁移计划：每个目标月份的新增/重复条数"""
        plans: List[Dict[str, Any]] = []
        for date_key in sorted(buckets.keys()):
            year = int(date_key[:4])
            month = int(date_key[5:7])
            blocks = buckets[date_key]

            existing = cls._existing_fingerprints(user, year, month)
            new_count = 0
            duplicate_count = 0
            for block in blocks:
                fingerprint = BeanFileManager._entry_fingerprint(block)
                if not fingerprint or fingerprint in existing:
                    duplicate_count += 1
                else:
                    new_count += 1
                    existing.add(fingerprint)

            plans.append({
                'year': year,
                'month': month,
                'target': BeanFileManager.get_monthly_relative_path(year, month),
                'new': new_count,
                'duplicate': duplicate_count,
            })
        return plans

    @classmethod
    def preview(cls, user) -> Dict[str, Any]:
        """预览迁移计划，不落盘、不提交

        Returns:
            Dict[str, Any]: 含 total_entries / files_scanned / plans / errors
        """
        if not hasattr(user, 'git_repo'):
            raise GitServiceException("用户未启用 Git 功能")

        collected = cls._collect_entries(user)
        plans = cls._build_plan(user, collected['buckets'])
        total_entries = sum(len(blocks) for blocks in collected['buckets'].values())

        return {
            'total_entries': total_entries,
            'files_scanned': len(collected['files']),
            'plans': plans,
            'errors': collected['errors'],
        }

    @classmethod
    def execute(cls, user) -> Dict[str, Any]:
        """执行迁移：写入月度文件 → 提交推送 → 清空 trans/ 条目

        Raises:
            GitServiceException: 未启用 Git，或存在解析失败文件（整单中止）
        """
        if not hasattr(user, 'git_repo'):
            raise GitServiceException("用户未启用 Git 功能")

        collected = cls._collect_entries(user)

        if collected['errors']:
            first = collected['errors'][0]
            raise GitServiceException(
                f"存在无法解析的文件，已中止迁移: {first['file']} ({first['error']})"
            )

        buckets = collected['buckets']
        if not buckets:
            return {
                'status': 'skipped',
                'message': 'trans/ 下没有可迁移的条目',
                'plans': [],
                'entries_appended': 0,
                'entries_duplicated': 0,
                'files_cleared': 0,
                'push': None,
            }

        plans = cls._build_plan(user, buckets)

        total_appended = 0
        total_skipped = 0
        years = set()
        for date_key in sorted(buckets.keys()):
            year = int(date_key[:4])
            month = int(date_key[5:7])
            years.add(year)
            result = BeanFileManager.append_entries_to_monthly(
                user, year, month, buckets[date_key]
            )
            total_appended += result['appended']
            total_skipped += result['skipped']

        # 提交推送：仅包含受影响年度目录与根 main.bean
        paths = [f"{year}/" for year in sorted(years)] + ['main.bean']
        push_result = PlatformGitService().push_ledger(user, paths=paths)

        # 推送成功后才清空 trans/，失败则条目保留以便重试
        files_cleared = BeanFileManager.clear_trans_entries(user)

        logger.info(
            "Ledger commit for %s: appended=%d skipped=%d cleared=%d push=%s",
            getattr(user, 'username', user),
            total_appended,
            total_skipped,
            files_cleared,
            push_result.get('status'),
        )

        return {
            'status': 'success',
            'message': '已迁移到月度账本并推送到远程仓库',
            'plans': plans,
            'entries_appended': total_appended,
            'entries_duplicated': total_skipped,
            'files_cleared': files_cleared,
            'push': push_result,
        }
