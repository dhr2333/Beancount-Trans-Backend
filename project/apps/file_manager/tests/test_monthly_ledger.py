"""年月度账本能力测试

覆盖 BeanFileManager 新增的月度账本 API：
- 路径拼接（{year}/{MM}-expenses.bean、{year}/00.bean）
- ensure_year_structure（目录/12 月度文件/年度索引/main.bean include，幂等）
- split_entries 条目切分
- append_entries_to_monthly（追加 + 条目级去重）
- iter_trans_bean_files / clear_trans_entries

所有测试将 settings.ASSETS_BASE_PATH 指向 tmp_path，避免污染真实 Assets 目录。
"""
import os
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from project.utils.file import BeanFileManager

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def assets_dir(tmp_path, monkeypatch):
    base = tmp_path / 'Assets'
    base.mkdir()
    monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', str(base))
    return base


@pytest.fixture
def user(assets_dir):
    return User.objects.create_user(username='monthuser', password='testpass123')


def _read(path):
    return Path(path).read_text(encoding='utf-8')


def _main_include_lines(user):
    return [
        line.strip()
        for line in _read(BeanFileManager.get_main_bean_path(user)).splitlines()
        if line.strip().startswith('include ')
    ]


ENTRY_A = (
    '2025-05-01 * "商户A" "午餐"\n'
    '  Expenses:Food:Lunch          30.00 CNY\n'
    '  Assets:Savings:Web:Wechat   -30.00 CNY'
)
ENTRY_B = (
    '2025-05-02 * "商户B" "晚餐"\n'
    '  Expenses:Food:Dinner         50.00 CNY\n'
    '  Assets:Savings:Web:Wechat   -50.00 CNY'
)


class TestPaths:
    def test_monthly_relative_path(self):
        assert BeanFileManager.get_monthly_relative_path(2025, 5) == '2025/05-expenses.bean'
        assert BeanFileManager.get_monthly_relative_path(2025, 12) == '2025/12-expenses.bean'

    def test_year_index_relative_path(self):
        assert BeanFileManager.get_year_index_relative_path(2025) == '2025/00.bean'

    def test_monthly_bean_path(self, user, assets_dir):
        expected = os.path.join(str(assets_dir), user.username, '2025', '03-expenses.bean')

        assert BeanFileManager.get_monthly_bean_path(user, 2025, 3) == expected


class TestEnsureYearStructure:
    def test_creates_dir_month_files_and_index(self, user):
        BeanFileManager.ensure_year_structure(user, 2025)

        year_dir = Path(BeanFileManager.get_year_dir(user, 2025))
        assert year_dir.is_dir()
        for month in range(1, 13):
            assert (year_dir / f"{month:02d}-expenses.bean").is_file()

        index_text = _read(BeanFileManager.get_year_index_path(user, 2025))
        assert 'include "01-expenses.bean"' in index_text
        assert 'include "12-expenses.bean"' in index_text

        assert 'include "2025/00.bean"' in _main_include_lines(user)

    def test_is_idempotent(self, user):
        BeanFileManager.ensure_year_structure(user, 2025)
        index_before = _read(BeanFileManager.get_year_index_path(user, 2025))
        main_before = _read(BeanFileManager.get_main_bean_path(user))

        BeanFileManager.ensure_year_structure(user, 2025)

        assert _read(BeanFileManager.get_year_index_path(user, 2025)) == index_before
        assert _read(BeanFileManager.get_main_bean_path(user)) == main_before
        assert _main_include_lines(user).count('include "2025/00.bean"') == 1


class TestSplitEntries:
    def test_splits_by_date_and_ignores_non_entries(self):
        text = (
            '; 注释头\n'
            'option "title" "x"\n'
            '\n'
            '2025-05-01 * "a"\n'
            '  Expenses:A  1.00 CNY\n'
            '\n'
            '2025-06-02 * "b"\n'
            '  Expenses:B  2.00 CNY\n'
        )

        entries = BeanFileManager.split_entries(text)

        assert [date for date, _ in entries] == ['2025-05', '2025-06']
        assert 'Expenses:A' in entries[0][1]
        assert 'Expenses:B' in entries[1][1]

    def test_empty_text(self):
        assert BeanFileManager.split_entries('') == []


class TestAppendEntriesToMonthly:
    def test_appends_and_buckets(self, user):
        result = BeanFileManager.append_entries_to_monthly(user, 2025, 5, [ENTRY_A, ENTRY_B])

        assert result == {'appended': 2, 'skipped': 0}
        content = _read(BeanFileManager.get_monthly_bean_path(user, 2025, 5))
        assert '商户A' in content and '商户B' in content

    def test_dedup_skips_existing_entries(self, user):
        BeanFileManager.append_entries_to_monthly(user, 2025, 5, [ENTRY_A])

        result = BeanFileManager.append_entries_to_monthly(user, 2025, 5, [ENTRY_A, ENTRY_B])

        # ENTRY_A 重复被跳过，ENTRY_B 新增
        assert result == {'appended': 1, 'skipped': 1}
        content = _read(BeanFileManager.get_monthly_bean_path(user, 2025, 5))
        assert content.count('商户A') == 1

    def test_ensures_year_structure(self, user):
        BeanFileManager.append_entries_to_monthly(user, 2025, 5, [ENTRY_A])

        assert Path(BeanFileManager.get_year_index_path(user, 2025)).is_file()
        assert 'include "2025/00.bean"' in _main_include_lines(user)


class TestTransScanAndClear:
    def test_iter_trans_bean_files_excludes_index(self, user):
        trans_dir = Path(BeanFileManager._resolve_trans_path(user, ''))
        trans_dir.mkdir(parents=True, exist_ok=True)
        (trans_dir / 'a.bean').write_text(ENTRY_A, encoding='utf-8')
        sub = trans_dir / 'Test'
        sub.mkdir()
        (sub / 'b.bean').write_text(ENTRY_B, encoding='utf-8')

        files = BeanFileManager.iter_trans_bean_files(user)

        assert 'main.bean' not in files
        assert 'Test/b.bean' in files
        assert 'a.bean' in files
        assert files == sorted(files)

    def test_clear_trans_entries_keeps_header_only(self, user):
        trans_dir = Path(BeanFileManager._resolve_trans_path(user, ''))
        trans_dir.mkdir(parents=True, exist_ok=True)
        target = trans_dir / 'a.bean'
        target.write_text('; header\n\n' + ENTRY_A + '\n\n' + ENTRY_B + '\n', encoding='utf-8')

        cleared = BeanFileManager.clear_trans_entries(user)

        assert cleared == 1
        text = _read(target)
        assert '商户A' not in text and '商户B' not in text
        assert '; header' in text

    def test_clear_trans_entries_leaves_empty_files(self, user):
        trans_dir = Path(BeanFileManager._resolve_trans_path(user, ''))
        trans_dir.mkdir(parents=True, exist_ok=True)
        target = trans_dir / 'empty.bean'
        target.write_text('', encoding='utf-8')

        assert BeanFileManager.clear_trans_entries(user) == 0
        assert _read(target) == ''
