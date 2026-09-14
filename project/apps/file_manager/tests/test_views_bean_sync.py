"""文件管理视图的账本同步行为测试（Task 5）

覆盖 FileViewSet（create / destroy / batch_move）与 DirectoryViewSet
（update / destroy / batch_move）在操作文件系统镜像账本时的表现。

存储后端通过 patch project.apps.file_manager.views.get_storage_client 隔离，
ASSETS_BASE_PATH 指向 tmp_path，避免污染真实 Assets 目录。
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from project.apps.file_manager.models import Directory, File
from project.apps.translate.models import ParseFile
from project.utils.file import BeanFileManager

User = get_user_model()

pytestmark = pytest.mark.django_db

FILES_URL = '/api/files/'
DIRECTORIES_URL = '/api/directories/'


@pytest.fixture
def assets_dir(tmp_path, monkeypatch):
    base = tmp_path / 'Assets'
    base.mkdir()
    monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', str(base))
    return base


@pytest.fixture
def user(assets_dir):
    return User.objects.create_user(username='viewuser', password='testpass123')


@pytest.fixture
def client(user):
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def root_dir(user):
    return Directory.objects.get(owner=user, parent__isnull=True, name='Root')


@pytest.fixture
def storage_client():
    mock = MagicMock()
    mock.upload_file.return_value = True
    mock.delete_file.return_value = True
    mock.download_file.return_value = None
    with patch(
        'project.apps.file_manager.views.get_storage_client', return_value=mock
    ):
        yield mock


def _make_directory(user, parent, name):
    return Directory.objects.create(name=name, owner=user, parent=parent)


def _make_file(user, directory, name, content=''):
    """创建 File 记录并在 trans/ 镜像路径创建 .bean 文件与 include。"""
    file_obj = File.objects.create(
        name=name,
        directory=directory,
        storage_name=f'storage/{name}',
        size=len(content),
        owner=user,
        content_type='text/csv',
    )
    rel = BeanFileManager.create_bean_file(user, name, file_obj.get_bean_dir())
    if content:
        _bean_abs(user, rel).write_text(content, encoding='utf-8')
    BeanFileManager.add_bean_to_trans_main(user, rel)
    return file_obj


def _bean_abs(user, rel):
    return Path(BeanFileManager._resolve_trans_path(user, rel))


def _main_includes(user):
    main_path = BeanFileManager.get_trans_main_bean_path(user)
    return [
        line.strip()
        for line in Path(main_path).read_text(encoding='utf-8').splitlines()
        if line.strip().startswith('include ')
    ]


# --------------------------------------------------------------------------- #
# FileViewSet.create
# --------------------------------------------------------------------------- #
def test_file_create_in_subdirectory(client, user, root_dir, storage_client):
    sub = _make_directory(user, root_dir, 'Test')
    upload = SimpleUploadedFile(
        '202608_alipay.csv', b'a,b\n1,2\n', content_type='text/csv'
    )

    response = client.post(
        FILES_URL, {'directory': sub.id, 'file': upload}, format='multipart'
    )

    assert response.status_code == 201
    file_obj = File.objects.get(id=response.data['id'])
    assert file_obj.directory_id == sub.id
    assert ParseFile.objects.filter(file=file_obj).exists()
    assert _bean_abs(user, 'Test/202608_alipay.bean').is_file()
    assert 'include "Test/202608_alipay.bean"' in _main_includes(user)


# --------------------------------------------------------------------------- #
# FileViewSet.destroy
# --------------------------------------------------------------------------- #
def test_file_destroy_removes_bean_and_include(client, user, root_dir, storage_client):
    sub = _make_directory(user, root_dir, 'Test')
    file_obj = _make_file(user, sub, 'x.csv', content='data')
    assert _bean_abs(user, 'Test/x.bean').is_file()

    response = client.delete(f'{FILES_URL}{file_obj.id}/')

    assert response.status_code == 204
    assert not File.objects.filter(id=file_obj.id).exists()
    assert not _bean_abs(user, 'Test/x.bean').exists()
    assert 'include "Test/x.bean"' not in _main_includes(user)


# --------------------------------------------------------------------------- #
# FileViewSet.batch_move
# --------------------------------------------------------------------------- #
def test_file_batch_move_migrates_bean(client, user, root_dir, storage_client):
    a = _make_directory(user, root_dir, 'A')
    b = _make_directory(user, root_dir, 'B')
    file_obj = _make_file(user, a, 'x.csv', content='data')

    response = client.post(
        f'{FILES_URL}batch_move/',
        {'file_ids': [file_obj.id], 'target_directory_id': b.id},
        format='json',
    )

    assert response.status_code == 200
    assert response.data['moved'] == [file_obj.id]
    file_obj.refresh_from_db()
    assert file_obj.directory_id == b.id
    assert not _bean_abs(user, 'A/x.bean').exists()
    assert _bean_abs(user, 'B/x.bean').is_file()
    includes = _main_includes(user)
    assert 'include "B/x.bean"' in includes
    assert 'include "A/x.bean"' not in includes


def test_file_batch_move_conflict_keeps_db_unchanged(
    client, user, root_dir, storage_client
):
    a = _make_directory(user, root_dir, 'A')
    b = _make_directory(user, root_dir, 'B')
    file_obj = _make_file(user, a, 'x.csv', content='data')

    # 目标账本位置已存在同名 .bean（磁盘冲突）
    stray = _bean_abs(user, 'B/x.bean')
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_text('STRAY', encoding='utf-8')

    response = client.post(
        f'{FILES_URL}batch_move/',
        {'file_ids': [file_obj.id], 'target_directory_id': b.id},
        format='json',
    )

    assert response.status_code == 400
    assert response.data['details'][0]['file_id'] == file_obj.id
    # DB 与磁盘均保持原状
    file_obj.refresh_from_db()
    assert file_obj.directory_id == a.id
    assert _bean_abs(user, 'A/x.bean').is_file()
    assert stray.read_text(encoding='utf-8') == 'STRAY'
    includes = _main_includes(user)
    assert 'include "A/x.bean"' in includes
    assert 'include "B/x.bean"' not in includes


# --------------------------------------------------------------------------- #
# DirectoryViewSet.update
# --------------------------------------------------------------------------- #
def test_directory_update_rename_migrates_subtree(client, user, root_dir):
    a = _make_directory(user, root_dir, 'A')
    _make_file(user, a, 'x.csv', content='data')

    response = client.patch(
        f'{DIRECTORIES_URL}{a.id}/', {'name': 'C'}, format='json'
    )

    assert response.status_code == 200
    a.refresh_from_db()
    assert a.name == 'C'
    assert not _bean_abs(user, 'A/x.bean').exists()
    assert _bean_abs(user, 'C/x.bean').is_file()
    includes = _main_includes(user)
    assert 'include "C/x.bean"' in includes
    assert 'include "A/x.bean"' not in includes


def test_directory_update_conflict_returns_400_and_rolls_back(
    client, user, root_dir
):
    a = _make_directory(user, root_dir, 'A')
    _make_file(user, a, 'x.csv', content='data')

    # 仅存在于磁盘的 trans/Z 目录，使得 move_bean_dir 抛 FileExistsError
    stray = _bean_abs(user, 'Z/stray.bean')
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_text('stray', encoding='utf-8')

    response = client.patch(
        f'{DIRECTORIES_URL}{a.id}/', {'name': 'Z'}, format='json'
    )

    assert response.status_code == 400
    assert 'error' in response.data
    a.refresh_from_db()
    assert a.name == 'A'  # DB 变更已回滚
    assert _bean_abs(user, 'A/x.bean').is_file()
    assert 'include "A/x.bean"' in _main_includes(user)


# --------------------------------------------------------------------------- #
# DirectoryViewSet.batch_move
# --------------------------------------------------------------------------- #
def test_directory_batch_move_migrates_subtree(client, user, root_dir):
    a = _make_directory(user, root_dir, 'A')
    sub = _make_directory(user, a, 'sub')
    _make_file(user, a, 'x.csv', content='x')
    _make_file(user, sub, 'y.csv', content='y')
    target = _make_directory(user, root_dir, 'T')

    response = client.post(
        f'{DIRECTORIES_URL}batch_move/',
        {'directory_ids': [a.id], 'target_directory_id': target.id},
        format='json',
    )

    assert response.status_code == 200
    assert response.data['moved'] == [a.id]
    a.refresh_from_db()
    assert a.parent_id == target.id
    assert _bean_abs(user, 'T/A/x.bean').is_file()
    assert _bean_abs(user, 'T/A/sub/y.bean').is_file()
    includes = _main_includes(user)
    assert 'include "T/A/x.bean"' in includes
    assert 'include "T/A/sub/y.bean"' in includes
    assert 'include "A/x.bean"' not in includes


# --------------------------------------------------------------------------- #
# DirectoryViewSet.destroy
# --------------------------------------------------------------------------- #
def test_directory_destroy_removes_subtree(client, user, root_dir, storage_client):
    a = _make_directory(user, root_dir, 'A')
    sub = _make_directory(user, a, 'sub')
    file_a = _make_file(user, a, 'x.csv', content='x')
    file_sub = _make_file(user, sub, 'y.csv', content='y')

    response = client.delete(f'{DIRECTORIES_URL}{a.id}/')

    assert response.status_code == 204
    assert not Directory.objects.filter(id=a.id).exists()
    assert not Directory.objects.filter(id=sub.id).exists()
    assert not File.objects.filter(id__in=[file_a.id, file_sub.id]).exists()
    assert not _bean_abs(user, 'A/x.bean').exists()
    assert not _bean_abs(user, 'A/sub/y.bean').exists()
    trans_a = Path(BeanFileManager.get_user_assets_path(user)) / 'trans' / 'A'
    assert not trans_a.exists()
    assert not any(
        line.startswith('include "A/') for line in _main_includes(user)
    )
