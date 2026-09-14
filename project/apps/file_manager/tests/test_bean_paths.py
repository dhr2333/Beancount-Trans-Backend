"""账本路径镜像逻辑测试（Task 5）

覆盖：
- Directory.get_relative_path / File.get_bean_dir / File.get_bean_relative_path
- BeanFileManager 的 trans/ 子目录镜像、include 维护、移动与删除

所有测试将 settings.ASSETS_BASE_PATH 指向 tmp_path，避免污染真实 Assets 目录。
"""
import os
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from project.apps.file_manager.models import Directory, File
from project.utils.file import BeanFileManager

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def assets_dir(tmp_path, monkeypatch):
    """把 ASSETS_BASE_PATH 指向临时目录，隔离文件系统。"""
    base = tmp_path / 'Assets'
    base.mkdir()
    monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', str(base))
    return base


@pytest.fixture
def user(assets_dir):
    return User.objects.create_user(username='beanuser', password='testpass123')


@pytest.fixture
def root_dir(user):
    return Directory.objects.get(owner=user, parent__isnull=True, name='Root')


def _make_directory(user, parent, name):
    return Directory.objects.create(name=name, owner=user, parent=parent)


def _main_bean_text(user):
    return Path(BeanFileManager.get_trans_main_bean_path(user)).read_text(encoding='utf-8')


def _include_lines(user):
    return [
        line.strip()
        for line in _main_bean_text(user).splitlines()
        if line.strip().startswith('include ')
    ]


# --------------------------------------------------------------------------- #
# Directory.get_relative_path
# --------------------------------------------------------------------------- #
class TestDirectoryRelativePath:
    def test_root_returns_empty(self, root_dir):
        assert root_dir.get_relative_path() == ''

    def test_one_level(self, user, root_dir):
        child = _make_directory(user, root_dir, 'Test')
        assert child.get_relative_path() == 'Test'

    def test_nested(self, user, root_dir):
        a = _make_directory(user, root_dir, 'A')
        b = _make_directory(user, a, 'B')
        assert b.get_relative_path() == 'A/B'

    def test_broken_parent_cycle_terminates(self, user, root_dir):
        """损坏数据造成 parent 环时不应无限循环。"""
        a = _make_directory(user, root_dir, 'A')
        b = _make_directory(user, a, 'B')
        a.parent = b  # 人为制造环
        a.save()

        result = a.get_relative_path()

        assert isinstance(result, str)
        assert result != ''


# --------------------------------------------------------------------------- #
# File.get_bean_dir / get_bean_relative_path
# --------------------------------------------------------------------------- #
class TestFileBeanPath:
    def _make_file(self, user, directory, name):
        return File.objects.create(
            name=name,
            directory=directory,
            storage_name=f'storage/{name}',
            size=10,
            owner=user,
            content_type='text/csv',
        )

    def test_root_file(self, user, root_dir):
        file_obj = self._make_file(user, root_dir, '202608_alipay.csv')
        assert file_obj.get_bean_dir() == ''
        assert file_obj.get_bean_relative_path() == '202608_alipay.bean'

    def test_subdirectory_file(self, user, root_dir):
        sub = _make_directory(user, root_dir, 'Test')
        file_obj = self._make_file(user, sub, '202608_alipay.csv')
        assert file_obj.get_bean_dir() == 'Test'
        assert file_obj.get_bean_relative_path() == 'Test/202608_alipay.bean'

    def test_nested_directory_file(self, user, root_dir):
        a = _make_directory(user, root_dir, 'A')
        b = _make_directory(user, a, 'B')
        file_obj = self._make_file(user, b, 'bill.csv')
        assert file_obj.get_bean_dir() == 'A/B'
        assert file_obj.get_bean_relative_path() == 'A/B/bill.bean'


# --------------------------------------------------------------------------- #
# BeanFileManager.get_bean_file_path
# --------------------------------------------------------------------------- #
class TestGetBeanFilePath:
    def test_without_relative_dir(self, user):
        user_root = BeanFileManager.get_user_assets_path(user)
        expected = os.path.join(user_root, 'trans', '202608_alipay.bean')

        path = BeanFileManager.get_bean_file_path(user, '202608_alipay.csv')

        assert path == expected
        assert os.path.isdir(os.path.join(user_root, 'trans'))
        # 仅创建目录，不创建文件
        assert not os.path.exists(path)

    def test_with_relative_dir_creates_subdirectory(self, user):
        user_root = BeanFileManager.get_user_assets_path(user)
        expected_dir = os.path.join(user_root, 'trans', 'Test')

        path = BeanFileManager.get_bean_file_path(user, '202608_alipay.csv', 'Test')

        assert path == os.path.join(expected_dir, '202608_alipay.bean')
        assert os.path.isdir(expected_dir)
        assert not os.path.exists(path)

    def test_relative_dir_is_normalized(self, user):
        user_root = BeanFileManager.get_user_assets_path(user)
        path = BeanFileManager.get_bean_file_path(user, 'x.csv', '/Test/Sub/')
        assert path == os.path.join(user_root, 'trans', 'Test', 'Sub', 'x.bean')


# --------------------------------------------------------------------------- #
# BeanFileManager.create_bean_file
# --------------------------------------------------------------------------- #
class TestCreateBeanFile:
    def test_creates_empty_file_and_returns_posix_relative_path(self, user):
        rel = BeanFileManager.create_bean_file(user, '202608_alipay.csv')

        assert rel == '202608_alipay.bean'
        user_root = BeanFileManager.get_user_assets_path(user)
        abs_path = os.path.join(user_root, 'trans', '202608_alipay.bean')
        assert os.path.isfile(abs_path)
        assert Path(abs_path).read_text(encoding='utf-8') == ''

    def test_creates_subdirectory_file(self, user):
        rel = BeanFileManager.create_bean_file(user, '202608_alipay.csv', 'Test')

        assert rel == 'Test/202608_alipay.bean'
        user_root = BeanFileManager.get_user_assets_path(user)
        abs_path = os.path.join(user_root, 'trans', 'Test', '202608_alipay.bean')
        assert os.path.isfile(abs_path)

    def test_get_bean_relative_path_static(self):
        assert BeanFileManager.get_bean_relative_path('a.csv') == 'a.bean'
        assert BeanFileManager.get_bean_relative_path('a.csv', 'Test') == 'Test/a.bean'


# --------------------------------------------------------------------------- #
# include 维护
# --------------------------------------------------------------------------- #
class TestTransMainInclude:
    def test_add_is_idempotent(self, user):
        BeanFileManager.create_bean_file(user, 'x.csv', 'Test')

        BeanFileManager.add_bean_to_trans_main(user, 'Test/x.bean')
        BeanFileManager.add_bean_to_trans_main(user, 'Test/x.bean')

        includes = _include_lines(user)
        assert includes.count('include "Test/x.bean"') == 1

    def test_add_normalizes_separators(self, user):
        BeanFileManager.add_bean_to_trans_main(user, os.path.join('Test', 'x.bean'))
        assert 'include "Test/x.bean"' in _include_lines(user)

    def test_remove(self, user):
        BeanFileManager.add_bean_to_trans_main(user, 'Test/x.bean')
        BeanFileManager.add_bean_to_trans_main(user, 'y.bean')

        BeanFileManager.remove_bean_from_trans_main(user, 'Test/x.bean')

        includes = _include_lines(user)
        assert 'include "Test/x.bean"' not in includes
        assert 'include "y.bean"' in includes

    def test_remove_missing_include_is_noop(self, user):
        BeanFileManager.ensure_trans_main_bean(user)
        before = _main_bean_text(user)

        BeanFileManager.remove_bean_from_trans_main(user, 'nope.bean')

        assert _main_bean_text(user) == before


# --------------------------------------------------------------------------- #
# delete / clear bean 文件
# --------------------------------------------------------------------------- #
class TestDeleteClearBeanFile:
    def test_clear_keeps_file_but_empties_content(self, user):
        rel = BeanFileManager.create_bean_file(user, 'x.csv', 'Test')
        user_root = BeanFileManager.get_user_assets_path(user)
        abs_path = os.path.join(user_root, 'trans', 'Test', 'x.bean')
        Path(abs_path).write_text('2025-01-20 * "a" "b"\n', encoding='utf-8')

        BeanFileManager.clear_bean_file(user, rel)

        assert os.path.isfile(abs_path)
        assert Path(abs_path).read_text(encoding='utf-8') == ''

    def test_delete_removes_mirrored_file_and_empty_dir(self, user):
        rel = BeanFileManager.create_bean_file(user, 'x.csv', 'Test')
        user_root = BeanFileManager.get_user_assets_path(user)
        abs_path = os.path.join(user_root, 'trans', 'Test', 'x.bean')

        BeanFileManager.delete_bean_file(user, rel)

        assert not os.path.exists(abs_path)
        # 遗留空目录被清理，但 trans/ 本身保留
        assert not os.path.isdir(os.path.join(user_root, 'trans', 'Test'))
        assert os.path.isdir(os.path.join(user_root, 'trans'))

    def test_delete_root_file_keeps_trans_dir(self, user):
        rel = BeanFileManager.create_bean_file(user, 'x.csv')
        BeanFileManager.delete_bean_file(user, rel)

        user_root = BeanFileManager.get_user_assets_path(user)
        assert os.path.isdir(os.path.join(user_root, 'trans'))


# --------------------------------------------------------------------------- #
# move_bean_file
# --------------------------------------------------------------------------- #
class TestMoveBeanFile:
    def test_move_rewrites_include(self, user):
        BeanFileManager.create_bean_file(user, 'x.csv', 'Test')
        BeanFileManager.add_bean_to_trans_main(user, 'Test/x.bean')
        user_root = BeanFileManager.get_user_assets_path(user)

        result = BeanFileManager.move_bean_file(user, 'Test/x.bean', 'Other/x.bean')

        assert result is True
        assert not os.path.exists(os.path.join(user_root, 'trans', 'Test', 'x.bean'))
        assert os.path.isfile(os.path.join(user_root, 'trans', 'Other', 'x.bean'))
        includes = _include_lines(user)
        assert 'include "Other/x.bean"' in includes
        assert 'include "Test/x.bean"' not in includes

    def test_move_missing_source_returns_false(self, user):
        assert BeanFileManager.move_bean_file(user, 'nope/x.bean', 'Other/x.bean') is False

    def test_move_to_existing_destination_raises_without_changes(self, user):
        BeanFileManager.create_bean_file(user, 'x.csv', 'Test')
        BeanFileManager.create_bean_file(user, 'x.csv', 'Other')
        BeanFileManager.add_bean_to_trans_main(user, 'Test/x.bean')
        user_root = BeanFileManager.get_user_assets_path(user)
        dest = os.path.join(user_root, 'trans', 'Other', 'x.bean')
        Path(dest).write_text('KEEP', encoding='utf-8')

        with pytest.raises(FileExistsError):
            BeanFileManager.move_bean_file(user, 'Test/x.bean', 'Other/x.bean')

        # 源文件与目标文件均未被改动，include 也未变化
        assert os.path.isfile(os.path.join(user_root, 'trans', 'Test', 'x.bean'))
        assert Path(dest).read_text(encoding='utf-8') == 'KEEP'
        includes = _include_lines(user)
        assert 'include "Test/x.bean"' in includes
        assert 'include "Other/x.bean"' not in includes


# --------------------------------------------------------------------------- #
# move_bean_dir
# --------------------------------------------------------------------------- #
class TestMoveBeanDir:
    def _seed_tree(self, user):
        """构建 trans/Test/{a.bean, sub/b.bean} 及对应 include。"""
        BeanFileManager.create_bean_file(user, 'a.csv', 'Test')
        BeanFileManager.create_bean_file(user, 'b.csv', 'Test/sub')
        BeanFileManager.add_bean_to_trans_main(user, 'Test/a.bean')
        BeanFileManager.add_bean_to_trans_main(user, 'Test/sub/b.bean')
        return BeanFileManager.get_user_assets_path(user)

    def test_move_to_new_dir_rewrites_prefix(self, user):
        user_root = self._seed_tree(user)

        result = BeanFileManager.move_bean_dir(user, 'Test', 'New')

        assert result is True
        assert os.path.isfile(os.path.join(user_root, 'trans', 'New', 'a.bean'))
        assert os.path.isfile(os.path.join(user_root, 'trans', 'New', 'sub', 'b.bean'))
        assert not os.path.isdir(os.path.join(user_root, 'trans', 'Test'))
        includes = _include_lines(user)
        assert 'include "New/a.bean"' in includes
        assert 'include "New/sub/b.bean"' in includes
        assert 'include "Test/a.bean"' not in includes

    def test_move_to_root_flattens_includes(self, user):
        user_root = self._seed_tree(user)

        result = BeanFileManager.move_bean_dir(user, 'Test', '')

        assert result is True
        assert os.path.isfile(os.path.join(user_root, 'trans', 'a.bean'))
        assert os.path.isfile(os.path.join(user_root, 'trans', 'sub', 'b.bean'))
        assert not os.path.isdir(os.path.join(user_root, 'trans', 'Test'))
        includes = _include_lines(user)
        assert 'include "a.bean"' in includes
        assert 'include "sub/b.bean"' in includes
        assert not any('Test/' in line for line in includes)

    def test_empty_old_dir_raises_value_error(self, user):
        with pytest.raises(ValueError):
            BeanFileManager.move_bean_dir(user, '', 'New')

    def test_missing_source_returns_false(self, user):
        assert BeanFileManager.move_bean_dir(user, 'Nope', 'New') is False

    def test_existing_destination_raises(self, user):
        self._seed_tree(user)
        BeanFileManager.create_bean_file(user, 'c.csv', 'Other')

        with pytest.raises(FileExistsError):
            BeanFileManager.move_bean_dir(user, 'Test', 'Other')


# --------------------------------------------------------------------------- #
# delete_bean_dir
# --------------------------------------------------------------------------- #
class TestDeleteBeanDir:
    def test_delete_removes_subtree_and_includes(self, user):
        BeanFileManager.create_bean_file(user, 'a.csv', 'Test')
        BeanFileManager.create_bean_file(user, 'b.csv', 'Test/sub')
        BeanFileManager.add_bean_to_trans_main(user, 'Test/a.bean')
        BeanFileManager.add_bean_to_trans_main(user, 'Test/sub/b.bean')
        user_root = BeanFileManager.get_user_assets_path(user)

        result = BeanFileManager.delete_bean_dir(user, 'Test')

        assert result is True
        assert not os.path.isdir(os.path.join(user_root, 'trans', 'Test'))
        includes = _include_lines(user)
        assert not any(line.startswith('include "Test/') for line in includes)

    def test_returns_false_for_empty_or_missing(self, user):
        assert BeanFileManager.delete_bean_dir(user, '') is False
        assert BeanFileManager.delete_bean_dir(user, '.') is False
        assert BeanFileManager.delete_bean_dir(user, 'Nope') is False

    def test_never_deletes_trans_root(self, user):
        user_root = BeanFileManager.get_user_assets_path(user)
        BeanFileManager.create_bean_file(user, 'a.csv')

        assert BeanFileManager.delete_bean_dir(user, '') is False
        assert BeanFileManager.delete_bean_dir(user, '.') is False
        assert os.path.isdir(os.path.join(user_root, 'trans'))
