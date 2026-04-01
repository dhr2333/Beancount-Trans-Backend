"""_clone_repository：ls-remote 失败须抛错，不得当作空仓库跳过。"""

from unittest.mock import patch, MagicMock

import pytest
from django.contrib.auth import get_user_model

from ..models import GitRepository
from ..services import PlatformGitService, GitServiceException

User = get_user_model()


@pytest.mark.django_db
@patch("project.apps.git_repository.services.subprocess.run")
def test_clone_raises_when_ls_remote_fails(mock_run, tmp_path):
    user = User.objects.create_user(username="lsremote_user", password="x")
    repo_dir = tmp_path / "my-assets"
    repo_dir.mkdir()

    git_repo = GitRepository.objects.create(
        owner=user,
        repo_name="my-assets",
        remote_ssh_url="git@github.com:org/repo.git",
        deploy_key_private="-----BEGIN PRIVATE KEY-----\nMII\n-----END PRIVATE KEY-----\n",
        deploy_key_public="ssh-rsa AAAAB3",
        setup_mode="link",
        provider="github",
    )

    failed = MagicMock()
    failed.returncode = 128
    failed.stdout = ""
    failed.stderr = "git@github.com: Permission denied (publickey).\n"
    mock_run.return_value = failed

    svc = PlatformGitService()
    svc.assets_base_path = tmp_path

    with pytest.raises(GitServiceException) as exc_info:
        svc._clone_repository(git_repo, repo_dir)

    assert "Deploy Key" in str(exc_info.value) or "无法访问远程" in str(exc_info.value)
    mock_run.assert_called_once()


@pytest.mark.django_db
@patch("project.apps.git_repository.services.subprocess.run")
def test_clone_skips_only_when_ls_remote_ok_but_empty(mock_run, tmp_path):
    user = User.objects.create_user(username="empty_remote_user", password="x")
    repo_dir = tmp_path / "empty-assets"
    repo_dir.mkdir()

    git_repo = GitRepository.objects.create(
        owner=user,
        repo_name="empty-assets",
        remote_ssh_url="git@github.com:org/empty.git",
        deploy_key_private="-----BEGIN PRIVATE KEY-----\nMII\n-----END PRIVATE KEY-----\n",
        deploy_key_public="ssh-rsa AAAAB3",
        setup_mode="link",
        provider="github",
    )

    empty_ok = MagicMock()
    empty_ok.returncode = 0
    empty_ok.stdout = ""
    empty_ok.stderr = ""
    mock_run.return_value = empty_ok

    svc = PlatformGitService()
    svc.assets_base_path = tmp_path

    svc._clone_repository(git_repo, repo_dir)

    mock_run.assert_called_once()


def _fake_clone_ok(_git_repo, dest):
    dest.mkdir(parents=True, exist_ok=True)
    (dest / ".git").mkdir()


@pytest.mark.django_db
@patch("project.apps.git_repository.services.PlatformGitService._clone_repository")
@patch("project.apps.git_repository.services.PlatformGitService._pull_repository")
def test_sync_first_clone_replaces_local_only_after_successful_clone(mock_pull, mock_clone, tmp_path):
    """首次同步：仅在 clone 成功后替换目录；clone 指向临时目录而非直接覆盖用户路径。"""
    mock_clone.side_effect = _fake_clone_ok
    user = User.objects.create_user(username="sync_rmtree_user", password="x")
    repo_name = "t1-assets"
    target = tmp_path / repo_name
    target.mkdir(parents=True)
    (target / "local_only.txt").write_text("x", encoding="utf-8")

    GitRepository.objects.create(
        owner=user,
        repo_name=repo_name,
        remote_ssh_url="git@github.com:org/repo.git",
        deploy_key_private="-----BEGIN PRIVATE KEY-----\nMII\n-----END PRIVATE KEY-----\n",
        deploy_key_public="ssh-rsa AAAAB3",
        setup_mode="link",
        provider="github",
    )

    svc = PlatformGitService()
    svc.assets_base_path = tmp_path

    result = svc.sync_repository(user)

    assert result["status"] == "success"
    mock_pull.assert_not_called()
    mock_clone.assert_called_once()
    assert mock_clone.call_args[0][0].repo_name == repo_name
    clone_dest = mock_clone.call_args[0][1]
    assert clone_dest != target
    assert clone_dest.name.startswith(f"clone-{repo_name}-")
    assert not (target / "local_only.txt").exists()
    assert (target / ".git").is_dir()


@pytest.mark.django_db
@patch("project.apps.git_repository.services.PlatformGitService._clone_repository")
@patch("project.apps.git_repository.services.PlatformGitService._pull_repository")
def test_sync_first_clone_failure_preserves_local_ledger(mock_pull, mock_clone, tmp_path):
    """clone/ls-remote 失败时不得删除用户本地账本目录内容。"""
    mock_clone.side_effect = GitServiceException(
        "无法访问远程仓库，请检查 Deploy Key 是否已添加到托管平台且具备读权限。"
    )
    user = User.objects.create_user(username="sync_preserve_user", password="x")
    repo_name = "t2-assets"
    target = tmp_path / repo_name
    target.mkdir(parents=True)
    (target / "ledger.bean").write_text("2010-01-01 open Assets:Cash", encoding="utf-8")

    GitRepository.objects.create(
        owner=user,
        repo_name=repo_name,
        remote_ssh_url="git@github.com:org/repo.git",
        deploy_key_private="-----BEGIN PRIVATE KEY-----\nMII\n-----END PRIVATE KEY-----\n",
        deploy_key_public="ssh-rsa AAAAB3",
        setup_mode="link",
        provider="github",
    )

    svc = PlatformGitService()
    svc.assets_base_path = tmp_path

    result = svc.sync_repository(user)

    assert result["status"] == "failed"
    mock_pull.assert_not_called()
    assert (target / "ledger.bean").exists()
    assert not (target / ".git").exists()
