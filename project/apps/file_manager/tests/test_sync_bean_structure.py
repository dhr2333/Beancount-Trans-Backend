"""存量账本结构对齐命令 sync_bean_structure 测试（Task 5）

通过 django.core.management.call_command 调用命令，验证：
- 扁平 trans/x.bean 迁移到镜像目录 trans/Test/x.bean 并重写 include
- 反复执行幂等
- --dry-run 不落地任何改动
- 目标已存在时不覆盖
- --user 只处理指定用户

ASSETS_BASE_PATH 指向 tmp_path，避免污染真实 Assets 目录。
"""
import io
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command

from project.apps.file_manager.models import Directory, File
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
    return User.objects.create_user(username='syncuser', password='testpass123')


@pytest.fixture
def root_dir(user):
    return Directory.objects.get(owner=user, parent__isnull=True, name='Root')


def _run(user=None, dry_run=False):
    out = io.StringIO()
    kwargs = {'stdout': out}
    if dry_run:
        kwargs['dry_run'] = True
    if user:
        kwargs['user'] = user
    call_command('sync_bean_structure', **kwargs)
    return out.getvalue()


def _make_file(user, directory, name):
    return File.objects.create(
        name=name,
        directory=directory,
        storage_name=f'storage/{name}',
        size=1,
        owner=user,
        content_type='text/csv',
    )


def _bean_abs(user, rel):
    return Path(BeanFileManager._resolve_trans_path(user, rel))


def _main_includes(user):
    main_path = BeanFileManager.get_trans_main_bean_path(user)
    return [
        line.strip()
        for line in Path(main_path).read_text(encoding='utf-8').splitlines()
        if line.strip().startswith('include ')
    ]


def _trans_listing(user):
    trans = Path(BeanFileManager._resolve_trans_path(user, ''))
    return sorted(
        str(path.relative_to(trans)) for path in trans.rglob('*') if path.is_file()
    )


# --------------------------------------------------------------------------- #
# 迁移
# --------------------------------------------------------------------------- #
def test_migrates_flat_bean_to_mirrored_dir(user, root_dir):
    test_dir = Directory.objects.create(name='Test', owner=user, parent=root_dir)
    _make_file(user, test_dir, 'x.csv')
    flat = _bean_abs(user, 'x.bean')
    flat.write_text('FLAT', encoding='utf-8')
    BeanFileManager.add_bean_to_trans_main(user, 'x.bean')

    out = _run()

    assert not flat.exists()
    moved = _bean_abs(user, 'Test/x.bean')
    assert moved.is_file()
    assert moved.read_text(encoding='utf-8') == 'FLAT'
    includes = _main_includes(user)
    assert 'include "Test/x.bean"' in includes
    assert 'include "x.bean"' not in includes
    assert '迁移 1 个' in out


# --------------------------------------------------------------------------- #
# 幂等
# --------------------------------------------------------------------------- #
def test_second_run_is_idempotent(user, root_dir):
    test_dir = Directory.objects.create(name='Test', owner=user, parent=root_dir)
    _make_file(user, test_dir, 'x.csv')
    _bean_abs(user, 'x.bean').write_text('FLAT', encoding='utf-8')

    _run()
    main_after_first = Path(
        BeanFileManager.get_trans_main_bean_path(user)
    ).read_text(encoding='utf-8')
    listing_after_first = _trans_listing(user)

    out_second = _run()

    assert Path(
        BeanFileManager.get_trans_main_bean_path(user)
    ).read_text(encoding='utf-8') == main_after_first
    assert _trans_listing(user) == listing_after_first
    assert '迁移 0 个' in out_second
    assert '已对齐 1 个' in out_second


# --------------------------------------------------------------------------- #
# dry-run
# --------------------------------------------------------------------------- #
def test_dry_run_makes_no_changes(user, root_dir):
    test_dir = Directory.objects.create(name='Test', owner=user, parent=root_dir)
    _make_file(user, test_dir, 'x.csv')
    flat = _bean_abs(user, 'x.bean')
    flat.write_text('FLAT', encoding='utf-8')
    main_before = Path(
        BeanFileManager.get_trans_main_bean_path(user)
    ).read_text(encoding='utf-8')

    out = _run(dry_run=True)

    assert flat.is_file()
    assert not _bean_abs(user, 'Test/x.bean').exists()
    assert Path(
        BeanFileManager.get_trans_main_bean_path(user)
    ).read_text(encoding='utf-8') == main_before
    assert '计划移动: x.bean -> Test/x.bean' in out


# --------------------------------------------------------------------------- #
# 目标已存在
# --------------------------------------------------------------------------- #
def test_existing_target_is_not_overwritten(user, root_dir):
    test_dir = Directory.objects.create(name='Test', owner=user, parent=root_dir)
    _make_file(user, test_dir, 'x.csv')
    target = _bean_abs(user, 'Test/x.bean')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('TARGET', encoding='utf-8')
    flat = _bean_abs(user, 'x.bean')
    flat.write_text('FLAT', encoding='utf-8')

    _run()

    assert target.read_text(encoding='utf-8') == 'TARGET'
    assert flat.is_file()  # 未移动
    assert 'include "Test/x.bean"' in _main_includes(user)


# --------------------------------------------------------------------------- #
# --user 限制
# --------------------------------------------------------------------------- #
def test_user_filter_only_processes_target_user(user, root_dir):
    other = User.objects.create_user(username='otheruser', password='testpass123')
    other_root = Directory.objects.get(
        owner=other, parent__isnull=True, name='Root'
    )

    test_dir = Directory.objects.create(name='Test', owner=user, parent=root_dir)
    _make_file(user, test_dir, 'x.csv')
    _bean_abs(user, 'x.bean').write_text('FLAT', encoding='utf-8')

    other_dir = Directory.objects.create(name='Other', owner=other, parent=other_root)
    _make_file(other, other_dir, 'y.csv')
    other_flat = _bean_abs(other, 'y.bean')
    other_flat.write_text('FLAT2', encoding='utf-8')

    _run(user=user.username)

    # 目标用户已迁移
    assert _bean_abs(user, 'Test/x.bean').is_file()
    assert not _bean_abs(user, 'x.bean').exists()
    # 其他用户不受影响
    assert other_flat.is_file()
    assert not _bean_abs(other, 'Other/y.bean').exists()
    assert 'include "Other/y.bean"' not in _main_includes(other)
