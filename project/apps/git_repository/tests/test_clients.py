import pytest
from unittest.mock import patch, MagicMock
import requests

from ..clients import GiteaAPIClient, GiteaAPIException


class TestGiteaAPIClient:
    """Gitea API 客户端测试"""

    def setup_method(self):
        """测试设置"""
        with patch('project.apps.git_repository.clients.settings') as mock_settings:
            mock_settings.GITEA_BASE_URL = 'https://gitea.test.com'
            mock_settings.GITEA_ADMIN_TOKEN = 'test_token'
            mock_settings.GITEA_ORG_NAME = 'test-org'
            self.client = GiteaAPIClient()

    def test_init_missing_token(self):
        """测试缺少 token 时的初始化错误"""
        with patch('project.apps.git_repository.clients.settings') as mock_settings:
            mock_settings.GITEA_BASE_URL = 'https://gitea.test.com'
            mock_settings.GITEA_ADMIN_TOKEN = ''
            mock_settings.GITEA_ORG_NAME = 'test-org'

            with pytest.raises(ValueError, match="GITEA_ADMIN_TOKEN environment variable is required"):
                GiteaAPIClient()

    @patch('requests.Session.request')
    def test_make_request_success(self, mock_request):
        """测试成功的 API 请求"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 123, 'name': 'test-repo'}
        mock_response.content = b'{"id": 123}'
        mock_request.return_value = mock_response

        result = self.client._make_request('GET', '/repos/test-org/test-repo')

        assert result == {'id': 123, 'name': 'test-repo'}
        mock_request.assert_called_once_with(
            'GET', 
            'https://gitea.test.com/api/v1/repos/test-org/test-repo'
        )

    @patch('requests.Session.request')
    def test_make_request_error(self, mock_request):
        """测试 API 请求错误"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {'message': 'Repository not found'}
        mock_request.return_value = mock_response

        with pytest.raises(GiteaAPIException) as exc_info:
            self.client._make_request('GET', '/repos/test-org/nonexistent')

        assert exc_info.value.status_code == 404

    @patch('requests.Session.request')
    def test_make_request_network_error(self, mock_request):
        """测试网络错误"""
        mock_request.side_effect = requests.RequestException('Network error')

        with pytest.raises(GiteaAPIException, match="Network error"):
            self.client._make_request('GET', '/test')

    @patch.object(GiteaAPIClient, '_make_request')
    def test_create_repository_success(self, mock_request):
        """测试成功创建仓库"""
        mock_request.return_value = {
            'id': 123,
            'name': 'test-repo',
            'clone_url': 'https://gitea.test.com/test-org/test-repo.git'
        }

        result = self.client.create_repository(
            repo_name='test-repo',
            description='Test repository',
            private=True
        )

        assert result['id'] == 123
        assert result['name'] == 'test-repo'

        # 验证请求参数
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == 'POST'
        assert args[1] == '/orgs/test-org/repos'

        expected_data = {
            'name': 'test-repo',
            'description': 'Test repository',
            'private': True,
            'auto_init': False,
            'default_branch': 'main',
            'has_issues': False,
            'has_wiki': False,
            'has_pull_requests': False,
            'has_projects': False,
            'archived': False
        }
        assert kwargs['json'] == expected_data

    @patch.object(GiteaAPIClient, '_make_request')
    def test_delete_repository(self, mock_request):
        """测试删除仓库"""
        mock_request.return_value = {}

        self.client.delete_repository('test-repo')

        mock_request.assert_called_once_with('DELETE', '/repos/test-org/test-repo')

    @patch.object(GiteaAPIClient, '_make_request')
    def test_add_deploy_key(self, mock_request):
        """测试添加 Deploy Key"""
        mock_request.return_value = {
            'id': 456,
            'title': 'Test Deploy Key',
            'key': 'ssh-rsa AAAAB3...'
        }

        result = self.client.add_deploy_key(
            repo_name='test-repo',
            title='Test Deploy Key',
            public_key='ssh-rsa AAAAB3...',
            read_only=False
        )

        assert result['id'] == 456
        assert result['title'] == 'Test Deploy Key'

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == 'POST'
        assert args[1] == '/repos/test-org/test-repo/keys'

        expected_data = {
            'title': 'Test Deploy Key',
            'key': 'ssh-rsa AAAAB3...',
            'read_only': False
        }
        assert kwargs['json'] == expected_data

    @patch.object(GiteaAPIClient, '_make_request')
    def test_delete_deploy_key(self, mock_request):
        """测试删除 Deploy Key"""
        mock_request.return_value = {}

        self.client.delete_deploy_key('test-repo', 456)

        mock_request.assert_called_once_with('DELETE', '/repos/test-org/test-repo/keys/456')

    @patch.object(GiteaAPIClient, '_make_request')
    def test_create_webhook(self, mock_request):
        """测试创建 Webhook"""
        mock_request.return_value = {
            'id': 789,
            'type': 'gitea',
            'active': True
        }

        result = self.client.create_webhook(
            repo_name='test-repo',
            webhook_url='https://example.com/webhook',
            secret='webhook_secret'
        )

        assert result['id'] == 789
        assert result['type'] == 'gitea'

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == 'POST'
        assert args[1] == '/repos/test-org/test-repo/hooks'

        expected_data = {
            'type': 'gitea',
            'config': {
                'url': 'https://example.com/webhook',
                'content_type': 'json',
                'secret': 'webhook_secret'
            },
            'events': ['push'],
            'active': True
        }
        assert kwargs['json'] == expected_data

    @patch.object(GiteaAPIClient, '_make_request')
    def test_get_repository_info(self, mock_request):
        """测试获取仓库信息"""
        mock_request.return_value = {
            'id': 123,
            'name': 'test-repo',
            'size': 1024  # KB
        }

        result = self.client.get_repository_info('test-repo')

        assert result['id'] == 123
        assert result['name'] == 'test-repo'
        mock_request.assert_called_once_with('GET', '/repos/test-org/test-repo')

    @patch.object(GiteaAPIClient, '_make_request')
    def test_get_repository_size(self, mock_request):
        """测试获取仓库大小"""
        mock_request.return_value = {
            'size': 1024  # KB
        }

        size = self.client.get_repository_size('test-repo')

        assert size == 1024 * 1024  # 转换为字节
        mock_request.assert_called_once_with('GET', '/repos/test-org/test-repo')

    @patch.object(GiteaAPIClient, '_make_request')
    def test_check_repository_exists_true(self, mock_request):
        """测试仓库存在检查 - 存在"""
        mock_request.return_value = {'id': 123}

        exists = self.client.check_repository_exists('test-repo')

        assert exists is True

    @patch.object(GiteaAPIClient, '_make_request')
    def test_check_repository_exists_false(self, mock_request):
        """测试仓库存在检查 - 不存在"""
        mock_request.side_effect = GiteaAPIException('Not found', status_code=404)

        exists = self.client.check_repository_exists('test-repo')

        assert exists is False

    @patch.object(GiteaAPIClient, '_make_request')
    def test_check_repository_exists_other_error(self, mock_request):
        """测试仓库存在检查 - 其他错误"""
        mock_request.side_effect = GiteaAPIException('Server error', status_code=500)

        with pytest.raises(GiteaAPIException):
            self.client.check_repository_exists('test-repo')

    @patch.object(GiteaAPIClient, '_make_request')
    def test_list_deploy_keys(self, mock_request):
        """测试获取 Deploy Key 列表"""
        mock_request.return_value = [
            {'id': 1, 'title': 'Key 1'},
            {'id': 2, 'title': 'Key 2'}
        ]

        keys = self.client.list_deploy_keys('test-repo')

        assert len(keys) == 2
        assert keys[0]['id'] == 1
        mock_request.assert_called_once_with('GET', '/repos/test-org/test-repo/keys')

