"""关联远程仓库：SSH 地址解析、平台自动识别与序列化器校验。"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from ..git_remote import (
    guess_provider_from_ssh,
    is_valid_ssh_git_url,
    parse_ssh_host,
)
from ..serializers import LinkRepositorySerializer
from ..services import PlatformGitService

User = get_user_model()


class TestParseSshHost:
    @pytest.mark.parametrize(
        'url,expected',
        [
            ('git@github.com:owner/repo.git', 'github.com'),
            ('ssh://git@gitlab.com/group/repo.git', 'gitlab.com'),
            ('ssh://git@git.example.com:2222/group/repo.git', 'git.example.com'),
            ('git@GitHub.com:owner/repo.git', 'github.com'),
            ('', ''),
            ('not-a-url', ''),
        ],
    )
    def test_parse_ssh_host(self, url, expected):
        assert parse_ssh_host(url) == expected


class TestGuessProviderFromSsh:
    @pytest.mark.parametrize(
        'url,expected',
        [
            ('git@github.com:owner/repo.git', 'github'),
            ('ssh://git@github.com/owner/repo.git', 'github'),
            ('ssh://git@git.company.github.com/owner/repo.git', 'github'),
            ('git@gitlab.com:group/repo.git', 'gitlab'),
            ('ssh://git@gitlab.example.com:2222/group/repo.git', 'gitlab'),
            ('git@git.gitea.example.com:owner/repo.git', 'gitea'),
            ('ssh://git@gogs.example.com/owner/repo.git', 'gogs'),
            ('git@gitee.com:owner/repo.git', 'other'),
            ('ssh://git@git.example.com:2222/group/repo.git', 'other'),
            ('', 'other'),
        ],
    )
    def test_guess_provider_from_ssh(self, url, expected):
        assert guess_provider_from_ssh(url) == expected


class TestIsValidSshGitUrl:
    @pytest.mark.parametrize(
        'url,expected',
        [
            ('git@github.com:owner/repo.git', True),
            ('git@git.example.com:2222/group/repo.git', True),
            ('ssh://git@git.example.com:2222/group/repo.git', True),
            ('https://gitlab.com/owner/repo.git', False),
            ('http://git.example.com/owner/repo.git', False),
            ('git@github.com:', False),
            ('', False),
            ('not-a-url', False),
        ],
    )
    def test_is_valid_ssh_git_url(self, url, expected):
        assert is_valid_ssh_git_url(url) is expected


class TestLinkRepositorySerializer:
    def test_provider_blank_is_valid(self):
        serializer = LinkRepositorySerializer(data={'remote_ssh_url': 'git@gitlab.com:o/r.git'})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data['provider'] == ''

    def test_provider_can_be_overridden(self):
        serializer = LinkRepositorySerializer(
            data={'remote_ssh_url': 'git@git.example.com:o/r.git', 'provider': 'gogs'}
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data['provider'] == 'gogs'

    def test_provider_unsupported_value_rejected(self):
        serializer = LinkRepositorySerializer(
            data={'remote_ssh_url': 'git@git.example.com:o/r.git', 'provider': 'bitbucket'}
        )
        assert not serializer.is_valid()
        assert 'provider' in serializer.errors

    def test_https_url_rejected(self):
        serializer = LinkRepositorySerializer(
            data={'remote_ssh_url': 'https://gitlab.com/o/r.git'}
        )
        assert not serializer.is_valid()
        assert 'remote_ssh_url' in serializer.errors

    def test_ssh_url_whitespace_stripped(self):
        serializer = LinkRepositorySerializer(
            data={'remote_ssh_url': '  git@gitea.example.com:o/r.git  '}
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data['remote_ssh_url'] == 'git@gitea.example.com:o/r.git'


def _prepare_service(tmp_path, username):
    """构造可用的 PlatformGitService：assets 根目录指向 tmp_path 并预建用户目录。"""
    (tmp_path / username).mkdir(parents=True, exist_ok=True)
    svc = PlatformGitService()
    svc.assets_base_path = tmp_path
    return svc


@pytest.mark.django_db
@patch('project.apps.git_repository.services.PlatformGitService._generate_ssh_key_pair')
def test_link_autodetects_provider_from_ssh_url(mock_keygen, tmp_path):
    user = User.objects.create_user(username='link_auto_user', password='x')
    svc = _prepare_service(tmp_path, user.username)
    mock_keygen.return_value = ('PRIVATE', 'ssh-rsa AAAAB3')

    git_repo = svc.link_external_repository(
        user=user,
        remote_ssh_url='git@gitlab.example.com:group/repo.git',
        provider='',
    )

    assert git_repo.provider == 'gitlab'
    assert git_repo.setup_mode == 'link'
    assert git_repo.external_full_name == 'group/repo'


@pytest.mark.django_db
@patch('project.apps.git_repository.services.PlatformGitService._generate_ssh_key_pair')
def test_link_respects_explicit_provider_override(mock_keygen, tmp_path):
    user = User.objects.create_user(username='link_override_user', password='x')
    svc = _prepare_service(tmp_path, user.username)
    mock_keygen.return_value = ('PRIVATE', 'ssh-rsa AAAAB3')

    git_repo = svc.link_external_repository(
        user=user,
        remote_ssh_url='ssh://git@git.example.com:2222/team/ledger.git',
        provider='gogs',
    )

    assert git_repo.provider == 'gogs'
    assert git_repo.external_full_name == 'team/ledger'
