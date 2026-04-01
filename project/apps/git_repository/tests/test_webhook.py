"""GitWebhookView：GitHub / GitLab / Gitea 验签与分支过滤（同步逻辑 mock）。"""

import hashlib
import hmac
import json

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch

from ..models import GitRepository

User = get_user_model()


def _github_sig(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _gitea_sig(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(username="wh_user", password="x")


@pytest.mark.django_db
@patch("project.apps.git_repository.views.PlatformGitService.sync_repository")
def test_github_webhook_valid_triggers_sync(mock_sync, api_client, user):
    mock_sync.return_value = {"status": "success"}
    secret = "whsec_github_test"
    GitRepository.objects.create(
        owner=user,
        repo_name="u1-assets",
        gitea_repo_id=None,
        deploy_key_private="priv",
        deploy_key_public="pub",
        external_full_name="owner/beancount-repo",
        webhook_secret=secret,
        provider="github",
        default_branch="main",
        setup_mode="link",
        remote_ssh_url="git@github.com:owner/beancount-repo.git",
    )
    payload = {
        "ref": "refs/heads/main",
        "repository": {"full_name": "owner/beancount-repo"},
    }
    raw = json.dumps(payload).encode("utf-8")
    url = reverse("git-webhook")
    response = api_client.post(
        url,
        data=raw,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=_github_sig(raw, secret),
    )
    assert response.status_code == status.HTTP_200_OK
    mock_sync.assert_called_once_with(user)


@pytest.mark.django_db
def test_github_webhook_invalid_signature(api_client, user):
    secret = "correct"
    GitRepository.objects.create(
        owner=user,
        repo_name="u2-assets",
        gitea_repo_id=None,
        deploy_key_private="priv",
        deploy_key_public="pub",
        external_full_name="o/r",
        webhook_secret=secret,
        provider="github",
        default_branch="main",
        setup_mode="link",
        remote_ssh_url="git@github.com:o/r.git",
    )
    payload = {"ref": "refs/heads/main", "repository": {"full_name": "o/r"}}
    raw = json.dumps(payload).encode("utf-8")
    url = reverse("git-webhook")
    response = api_client.post(
        url,
        data=raw,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256="sha256=deadbeef",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@patch("project.apps.git_repository.views.PlatformGitService.sync_repository")
def test_github_webhook_non_default_branch_ignored(mock_sync, api_client, user):
    secret = "s"
    GitRepository.objects.create(
        owner=user,
        repo_name="u3-assets",
        gitea_repo_id=None,
        deploy_key_private="priv",
        deploy_key_public="pub",
        external_full_name="o/r",
        webhook_secret=secret,
        provider="github",
        default_branch="main",
        setup_mode="link",
        remote_ssh_url="git@github.com:o/r.git",
    )
    payload = {"ref": "refs/heads/dev", "repository": {"full_name": "o/r"}}
    raw = json.dumps(payload).encode("utf-8")
    url = reverse("git-webhook")
    response = api_client.post(
        url,
        data=raw,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=_github_sig(raw, secret),
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data.get("status") == "ignored"
    mock_sync.assert_not_called()


@pytest.mark.django_db
@patch("project.apps.git_repository.views.PlatformGitService.sync_repository")
def test_gitlab_webhook_valid_token(mock_sync, api_client, user):
    mock_sync.return_value = {"status": "success"}
    secret = "gitlab_token_secret"
    GitRepository.objects.create(
        owner=user,
        repo_name="u4-assets",
        gitea_repo_id=None,
        deploy_key_private="priv",
        deploy_key_public="pub",
        external_full_name="group/proj",
        webhook_secret=secret,
        provider="gitlab",
        default_branch="main",
        setup_mode="link",
        remote_ssh_url="git@gitlab.com:group/proj.git",
    )
    payload = {
        "ref": "refs/heads/main",
        "project": {"path_with_namespace": "group/proj"},
    }
    raw = json.dumps(payload).encode("utf-8")
    url = reverse("git-webhook")
    response = api_client.post(
        url,
        data=raw,
        content_type="application/json",
        HTTP_X_GITLAB_TOKEN=secret,
    )
    assert response.status_code == status.HTTP_200_OK
    mock_sync.assert_called_once_with(user)


@pytest.mark.django_db
@override_settings(GITEA_WEBHOOK_SECRET="global_gitea", GIT_WEBHOOK_STRICT=True)
@patch("project.apps.git_repository.views.PlatformGitService.sync_repository")
def test_gitea_hosted_webhook_by_repo_name(mock_sync, api_client, user):
    mock_sync.return_value = {"status": "success"}
    GitRepository.objects.create(
        owner=user,
        repo_name="abc123-assets",
        gitea_repo_id=1,
        deploy_key_private="priv",
        deploy_key_public="pub",
        external_full_name="",
        webhook_secret="",
        provider="gitea_hosted",
        default_branch="main",
        setup_mode="create",
        remote_ssh_url="",
    )
    payload = {
        "ref": "refs/heads/main",
        "repository": {"name": "abc123-assets", "full_name": "org/abc123-assets"},
    }
    raw = json.dumps(payload).encode("utf-8")
    url = reverse("git-webhook")
    sig = _gitea_sig(raw, "global_gitea")
    response = api_client.post(
        url,
        data=raw,
        content_type="application/json",
        HTTP_X_GITEA_SIGNATURE=sig,
    )
    assert response.status_code == status.HTTP_200_OK
    mock_sync.assert_called_once_with(user)
