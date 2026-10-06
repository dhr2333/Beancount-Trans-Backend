"""LedgerCommitService（trans/ → 月度账本提交）与接口测试"""
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from project.apps.git_repository.models import GitRepository
from project.apps.git_repository.ledger_commit_service import LedgerCommitService
from project.apps.git_repository.services import PlatformGitService, GitServiceException
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
def git_user(assets_dir):
    user = User.objects.create_user(username='gituser', password='testpass123')
    repo = GitRepository.objects.create(
        owner=user,
        repo_name='gituser-assets',
        remote_ssh_url='git@example.com:org/repo.git',
        deploy_key_private='-----BEGIN PRIVATE KEY-----\nMII\n-----END PRIVATE KEY-----\n',
        deploy_key_public='ssh-rsa AAAA',
    )
    # 为用户创建 trans/ 写入缓冲
    trans_dir = Path(BeanFileManager._resolve_trans_path(user, ''))
    trans_dir.mkdir(parents=True, exist_ok=True)
    return user, repo


ENTRY_MAY = (
    '2025-05-01 * "商户A" "午餐"\n'
    '  Expenses:Food:Lunch          30.00 CNY\n'
    '  Assets:Savings:Web:Wechat   -30.00 CNY'
)
ENTRY_JUN = (
    '2025-06-02 * "商户B" "晚餐"\n'
    '  Expenses:Food:Dinner         50.00 CNY\n'
    '  Assets:Savings:Web:Wechat   -50.00 CNY'
)


def _write_trans(user, name, text):
    path = Path(BeanFileManager._resolve_trans_path(user, name))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def _monthly_text(user, year, month):
    path = BeanFileManager.get_monthly_bean_path(user, year, month)
    if not Path(path).exists():
        return ''
    return Path(path).read_text(encoding='utf-8')


class TestPreview:
    def test_plans_without_side_effects(self, git_user):
        user, _repo = git_user
        _write_trans(user, 'bill.bean', ENTRY_MAY + '\n\n' + ENTRY_JUN)

        result = LedgerCommitService.preview(user)

        assert result['total_entries'] == 2
        assert result['files_scanned'] == 1
        targets = {p['target']: p for p in result['plans']}
        assert targets['2025/05-expenses.bean']['new'] == 1
        assert targets['2025/06-expenses.bean']['new'] == 1
        # 未落盘
        assert not Path(BeanFileManager.get_monthly_bean_path(user, 2025, 5)).exists()

    def test_counts_duplicates_against_existing(self, git_user):
        user, _repo = git_user
        BeanFileManager.append_entries_to_monthly(user, 2025, 5, [ENTRY_MAY])
        _write_trans(user, 'bill.bean', ENTRY_MAY)

        result = LedgerCommitService.preview(user)

        plan = next(p for p in result['plans'] if p['target'] == '2025/05-expenses.bean')
        assert plan['new'] == 0
        assert plan['duplicate'] == 1


class TestExecute:
    def test_migrates_commits_and_clears(self, git_user):
        user, _repo = git_user
        _write_trans(user, 'bill.bean', ENTRY_MAY + '\n\n' + ENTRY_JUN)

        with patch.object(
            PlatformGitService, 'push_ledger',
            return_value={'status': 'success', 'message': 'ok', 'files': []},
        ) as mock_push:
            result = LedgerCommitService.execute(user)

        assert result['status'] == 'success'
        assert result['entries_appended'] == 2
        assert result['files_cleared'] == 1
        assert '商户A' in _monthly_text(user, 2025, 5)
        assert '商户B' in _monthly_text(user, 2025, 6)

        # 推送路径含年度目录与 main.bean
        called_paths = mock_push.call_args.kwargs['paths']
        assert '2025/' in called_paths
        assert 'main.bean' in called_paths

        # trans/ 条目已清空
        trans_text = Path(BeanFileManager._resolve_trans_path(user, 'bill.bean')).read_text('utf-8')
        assert '商户A' not in trans_text

    def test_skips_when_no_entries(self, git_user):
        user, _repo = git_user
        with patch.object(PlatformGitService, 'push_ledger') as mock_push:
            result = LedgerCommitService.execute(user)

        assert result['status'] == 'skipped'
        mock_push.assert_not_called()

    def test_push_failure_keeps_trans_entries(self, git_user):
        user, _repo = git_user
        _write_trans(user, 'bill.bean', ENTRY_MAY)

        with patch.object(
            PlatformGitService, 'push_ledger',
            side_effect=GitServiceException('推送失败: boom'),
        ):
            with pytest.raises(GitServiceException):
                LedgerCommitService.execute(user)

        trans_text = Path(BeanFileManager._resolve_trans_path(user, 'bill.bean')).read_text('utf-8')
        assert '商户A' in trans_text

    def test_requires_git_user(self, assets_dir):
        plain_user = User.objects.create_user(username='plain', password='testpass123')
        with pytest.raises(GitServiceException):
            LedgerCommitService.execute(plain_user)


class TestCommitApi:
    def test_preview_endpoint(self, git_user):
        user, _repo = git_user
        _write_trans(user, 'bill.bean', ENTRY_MAY)

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/git/trans/commit/preview/')

        assert response.status_code == 200
        assert response.data['total_entries'] == 1

    def test_commit_endpoint(self, git_user):
        user, _repo = git_user
        _write_trans(user, 'bill.bean', ENTRY_MAY)

        client = APIClient()
        client.force_authenticate(user=user)
        with patch.object(
            PlatformGitService, 'push_ledger',
            return_value={'status': 'success', 'message': 'ok', 'files': []},
        ):
            response = client.post('/api/git/trans/commit/')

        assert response.status_code == 200
        assert response.data['entries_appended'] == 1

    def test_download_endpoint_removed(self, git_user):
        user, _repo = git_user
        client = APIClient()
        client.force_authenticate(user=user)

        assert client.get('/api/git/trans/download/').status_code == 404
