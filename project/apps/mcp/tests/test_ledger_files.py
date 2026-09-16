"""账本文件只读访问的路径护栏测试。"""
import pytest

from project.apps.mcp.ledger_files import (
    LedgerFileError,
    read_ledger_file,
    resolve_ledger_file,
    user_assets_root,
)

from .conftest import SAMPLE_BEAN

pytestmark = pytest.mark.django_db(transaction=True)


class TestResolveLedgerFile:
    def test_resolves_main_bean(self, user, ledger_files):
        assert resolve_ledger_file(user, 'main.bean') == ledger_files['main']

    def test_resolves_nested_bean(self, user, ledger_files):
        assert resolve_ledger_file(user, '2024/01.bean') == ledger_files['nested']

    def test_rejects_blank_path(self, user, ledger_files):
        with pytest.raises(LedgerFileError, match='path 不能为空'):
            resolve_ledger_file(user, '   ')

    def test_rejects_parent_traversal(self, user, ledger_files):
        with pytest.raises(LedgerFileError, match='只允许读取自己账本目录内的文件'):
            resolve_ledger_file(user, '../outside.bean')

    def test_rejects_absolute_path_outside_root(self, user, ledger_files, tmp_path):
        outside = tmp_path / 'outside.bean'
        with pytest.raises(LedgerFileError, match='只允许读取自己账本目录内的文件'):
            resolve_ledger_file(user, str(outside))

    def test_rejects_symlink_escape(self, user, ledger_files, tmp_path):
        link = user_assets_root(user) / 'link.bean'
        link.symlink_to(tmp_path / 'outside.bean')
        with pytest.raises(LedgerFileError, match='只允许读取自己账本目录内的文件'):
            resolve_ledger_file(user, 'link.bean')

    def test_rejects_non_bean_suffix(self, user, ledger_files):
        with pytest.raises(LedgerFileError, match='后缀'):
            resolve_ledger_file(user, 'notes.txt')

    def test_rejects_missing_file(self, user, ledger_files):
        with pytest.raises(LedgerFileError, match='文件不存在'):
            resolve_ledger_file(user, 'nope.bean')

    def test_rejects_oversized_file(self, user, ledger_files, settings, monkeypatch):
        monkeypatch.setattr(settings, 'MCP_MAX_FILE_BYTES', 10)
        with pytest.raises(LedgerFileError, match='文件过大'):
            resolve_ledger_file(user, 'main.bean')


class TestReadLedgerFile:
    def test_returns_relative_path_and_content(self, user, ledger_files):
        ledger_file = read_ledger_file(user, 'main.bean')
        assert ledger_file.path == 'main.bean'
        assert ledger_file.content == SAMPLE_BEAN
        assert ledger_file.size_bytes == len(SAMPLE_BEAN.encode('utf-8'))

    def test_reads_nested_file(self, user, ledger_files):
        ledger_file = read_ledger_file(user, '2024/01.bean')
        assert ledger_file.path == '2024/01.bean'
        assert '咖啡' in ledger_file.content

    def test_blocks_traversal(self, user, ledger_files):
        with pytest.raises(LedgerFileError):
            read_ledger_file(user, '../../etc/passwd.bean')

    def test_isolated_between_users(self, user, other_user, ledger_files, other_assets):
        first = read_ledger_file(user, 'main.bean')
        second = read_ledger_file(other_user, 'main.bean')
        assert first.content == SAMPLE_BEAN
        assert '房租' in second.content
