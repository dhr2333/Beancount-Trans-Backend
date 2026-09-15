"""取消同步：清除服务器本地账本副本并暂停自动拉取。

覆盖服务层 clear_synced_ledger、sync_repository 暂停闸门，以及两个视图端点。
所有测试将 settings.ASSETS_BASE_PATH 指向 tmp_path，避免污染真实 Assets 目录。
"""

import hashlib
import hmac
import json
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status as http_status
from rest_framework.test import APIClient

from ..models import GitRepository
from ..services import PlatformGitService
from ..views import GitSyncCancelView, GitWebhookView

User = get_user_model()


def _create_user(username: str):
    return User.objects.create_user(username=username, password="x")


def _create_git_repo(user, repo_name: str, **overrides):
    payload = {
        "owner": user,
        "repo_name": repo_name,
        "remote_ssh_url": "git@github.com:org/repo.git",
        "deploy_key_private": "-----BEGIN PRIVATE KEY-----\nMII\n-----END PRIVATE KEY-----\n",
        "deploy_key_public": "ssh-rsa AAAAB3",
        "setup_mode": "link",
        "provider": "github",
    }
    payload.update(overrides)
    return GitRepository.objects.create(**payload)


def _prepare_service(monkeypatch, tmp_path, username: str, repo_name: str):
    """把 ASSETS_BASE_PATH 与服务的 assets_base_path 同时指向 tmp_path，构造仓库目录。

    Returns:
        (user, service, user_assets_path)
    """
    monkeypatch.setattr(settings, "ASSETS_BASE_PATH", str(tmp_path))
    user = _create_user(username)
    git_repo = _create_git_repo(user, repo_name)

    user_assets_path = tmp_path / repo_name
    (user_assets_path / "trans").mkdir(parents=True)
    (user_assets_path / "trans" / "x.bean").write_text(
        "2024-01-01 open Assets:Cash", encoding="utf-8"
    )
    (user_assets_path / "account").mkdir()
    (user_assets_path / "account" / "a.bean").write_text(
        "2024-01-01 open Expenses:Food", encoding="utf-8"
    )
    (user_assets_path / "main.bean").write_text("include \"trans/main.bean\"", encoding="utf-8")
    (user_assets_path / ".git").mkdir()
    (user_assets_path / ".git" / "HEAD").write_text("ref: refs/heads/main", encoding="utf-8")

    svc = PlatformGitService()
    svc.assets_base_path = tmp_path
    return user, git_repo, svc, user_assets_path


@pytest.mark.django_db
def test_clear_synced_ledger_keeps_trans_and_rebuilds_main(monkeypatch, tmp_path):
    """清除后仅保留 trans/ 与重建的 main.bean，且不动任何 Git 同步配置。"""
    user, git_repo, svc, user_assets_path = _prepare_service(
        monkeypatch, tmp_path, "clear_user", "clear-assets"
    )
    original_pk = git_repo.pk

    result = svc.clear_synced_ledger(user)

    # trans/ 保留
    assert (user_assets_path / "trans" / "x.bean").exists()
    # main.bean 由标准模板重建
    assert (user_assets_path / "main.bean").exists()
    assert 'include "trans/main.bean"' in (user_assets_path / "main.bean").read_text(
        encoding="utf-8"
    )
    # Git 同步引入的内容全部清除（.git 含账本历史快照，必须删除）
    assert not (user_assets_path / "account").exists()
    assert not (user_assets_path / ".git").exists()

    # 目录名与仓库记录均未变更
    assert user_assets_path.is_dir()
    git_repo.refresh_from_db()
    assert git_repo.pk == original_pk
    assert git_repo.repo_name == "clear-assets"
    assert git_repo.sync_paused is True

    # 返回结果可用于前端展示
    assert result["trans_preserved"] is True
    assert result["repo_name"] == "clear-assets"
    assert result["cleaned_files"]


@pytest.mark.django_db
def test_clear_synced_ledger_is_idempotent(monkeypatch, tmp_path):
    """重复执行不应报错，且 trans/ 内容始终保留。"""
    user, _git_repo, svc, user_assets_path = _prepare_service(
        monkeypatch, tmp_path, "clear_twice_user", "clear-twice-assets"
    )

    svc.clear_synced_ledger(user)
    svc.clear_synced_ledger(user)

    assert (user_assets_path / "trans" / "x.bean").exists()
    assert (user_assets_path / "main.bean").exists()


@pytest.mark.django_db
def test_clear_synced_ledger_rebuilds_when_dir_missing(monkeypatch, tmp_path):
    """目录不存在（从未同步）时仍应重建 main.bean 并置为已取消同步。"""
    monkeypatch.setattr(settings, "ASSETS_BASE_PATH", str(tmp_path))
    user = _create_user("clear_missing_user")
    git_repo = _create_git_repo(user, "clear-missing-assets")

    svc = PlatformGitService()
    svc.assets_base_path = tmp_path

    result = svc.clear_synced_ledger(user)

    user_assets_path = tmp_path / "clear-missing-assets"
    assert (user_assets_path / "main.bean").exists()
    assert result["trans_preserved"] is False
    git_repo.refresh_from_db()
    assert git_repo.sync_paused is True


@pytest.mark.django_db
@patch("project.apps.git_repository.services.PlatformGitService._pull_repository")
@patch("project.apps.git_repository.services.PlatformGitService._clone_repository")
def test_auto_sync_skipped_when_paused(mock_clone, mock_pull, monkeypatch, tmp_path):
    """已取消同步时自动拉取（Webhook）直接跳过，且不改写同步状态与本地内容。"""
    user, git_repo, svc, user_assets_path = _prepare_service(
        monkeypatch, tmp_path, "paused_user", "paused-assets"
    )
    git_repo.sync_status = "success"
    git_repo.sync_paused = True
    git_repo.save()

    ledger_before = (user_assets_path / "trans" / "x.bean").read_text(encoding="utf-8")

    result = svc.sync_repository(user)

    assert result["status"] == "paused"
    mock_clone.assert_not_called()
    mock_pull.assert_not_called()

    git_repo.refresh_from_db()
    # 保留最后一次同步结果，不因跳过而覆盖
    assert git_repo.sync_status == "success"
    assert git_repo.sync_paused is True
    assert (user_assets_path / "trans" / "x.bean").read_text(encoding="utf-8") == ledger_before


@pytest.mark.django_db
@patch("project.apps.git_repository.services.PlatformGitService._pull_repository")
@patch("project.apps.git_repository.services.PlatformGitService._clone_repository")
def test_manual_sync_resumes_and_pulls(mock_clone, mock_pull, monkeypatch, tmp_path):
    """手动同步是显式重新授权：解除暂停并执行拉取。"""
    user, git_repo, svc, _user_assets_path = _prepare_service(
        monkeypatch, tmp_path, "resume_user", "resume-assets"
    )
    git_repo.sync_paused = True
    git_repo.save()

    result = svc.sync_repository(user, manual=True)

    assert result["status"] == "success"
    git_repo.refresh_from_db()
    assert git_repo.sync_paused is False
    # 已有 .git/ 目录，走 pull 分支
    mock_pull.assert_called_once()
    mock_clone.assert_not_called()


@pytest.mark.django_db
@patch("project.apps.git_repository.services.PlatformGitService._pull_repository")
def test_clear_then_resume_keeps_trans(mock_pull, monkeypatch, tmp_path):
    """清除（删除 .git）后恢复同步走初次克隆分支，trans/ 不被冲掉。"""
    user, git_repo, svc, user_assets_path = _prepare_service(
        monkeypatch, tmp_path, "roundtrip_user", "roundtrip-assets"
    )

    svc.clear_synced_ledger(user)
    assert not (user_assets_path / ".git").exists()

    def _fake_clone(_git_repo, dest):
        dest.mkdir(parents=True, exist_ok=True)
        (dest / ".git").mkdir()

    with patch.object(
        PlatformGitService, "_clone_repository", side_effect=_fake_clone
    ):
        result = svc.sync_repository(user, manual=True)

    assert result["status"] == "success"
    assert (user_assets_path / "trans" / "x.bean").exists()


@pytest.mark.django_db
def test_cancel_view_returns_404_without_repository():
    """未启用 Git 的用户调用取消同步返回 404。"""
    user = _create_user("cancel_no_repo_user")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(reverse("git-sync-cancel"))

    assert response.status_code == http_status.HTTP_404_NOT_FOUND
    assert "error" in response.data


@pytest.mark.django_db
def test_cancel_view_clears_ledger(monkeypatch, tmp_path):
    """有仓库的用户调用取消同步返回 200 与可核验的清理结果。"""
    user, git_repo, svc, user_assets_path = _prepare_service(
        monkeypatch, tmp_path, "cancel_api_user", "cancel-api-assets"
    )
    monkeypatch.setattr(GitSyncCancelView, "get_git_service", lambda self: svc)

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(reverse("git-sync-cancel"))

    assert response.status_code == http_status.HTTP_200_OK
    assert set(response.data.keys()) == {
        "message", "cleaned_files", "trans_preserved", "repo_name"
    }
    assert response.data["trans_preserved"] is True
    assert response.data["repo_name"] == "cancel-api-assets"
    assert response.data["cleaned_files"]
    assert (user_assets_path / "trans" / "x.bean").exists()
    assert not (user_assets_path / ".git").exists()

    git_repo.refresh_from_db()
    assert git_repo.sync_paused is True


@pytest.mark.django_db
def test_sync_status_exposes_paused(monkeypatch, tmp_path):
    """同步状态接口需下发 paused 供前端展示「已取消同步」。"""
    user, git_repo, _svc, _path = _prepare_service(
        monkeypatch, tmp_path, "status_paused_user", "status-paused-assets"
    )
    git_repo.sync_paused = True
    git_repo.save()

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("git-sync-status"))

    assert response.status_code == http_status.HTTP_200_OK
    assert response.data["paused"] is True


@pytest.mark.django_db
def test_webhook_is_noop_when_paused(monkeypatch, tmp_path):
    """暂停期间 Webhook 返回 200 且 status=paused，避免远端因连续失败停用 Webhook。"""
    monkeypatch.setattr(settings, "ASSETS_BASE_PATH", str(tmp_path))
    user = _create_user("webhook_paused_user")
    git_repo = _create_git_repo(
        user,
        "webhook-paused-assets",
        provider="gitea_hosted",
        remote_ssh_url="",
        gitea_repo_id=1,
        webhook_secret="s3cret",
        sync_paused=True,
        sync_status="success",
    )

    svc = PlatformGitService()
    svc.assets_base_path = tmp_path
    monkeypatch.setattr(GitWebhookView, "get_git_service", lambda self: svc)

    payload = {
        "ref": "refs/heads/main",
        "repository": {"name": git_repo.repo_name, "full_name": git_repo.repo_name},
        "commits": [],
    }
    body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()

    client = APIClient()
    response = client.post(
        reverse("git-webhook"),
        data=body,
        content_type="application/json",
        HTTP_X_GITEA_SIGNATURE=signature,
    )

    assert response.status_code == http_status.HTTP_200_OK
    assert response.data["status"] == "paused"

    git_repo.refresh_from_db()
    assert git_repo.sync_paused is True
    assert git_repo.sync_status == "success"
