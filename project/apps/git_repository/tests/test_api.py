import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from ..models import GitRepository
from ..services import GitServiceException

User = get_user_model()


@pytest.mark.django_db
class TestGitRepositoryAPI:
    """Git 仓库 API 测试"""
    
    def setup_method(self):
        """测试设置"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_get_repository_not_found(self):
        """测试获取不存在的仓库"""
        url = reverse('git-repository-list')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
    
    def test_get_repository_success(self):
        """测试获取存在的仓库"""
        repo = GitRepository.objects.create(
            owner=self.user,
            repo_name='abc123-assets',
            gitea_repo_id=123,
            deploy_key_private='private_key_content',
            deploy_key_public='public_key_content'
        )
        
        url = reverse('git-repository-list')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == repo.id
        assert response.data['repo_name'] == 'abc123-assets'
        assert 'deploy_key_download_url' in response.data
    
    # @patch('project.apps.git_repository.views.PlatformGitService')
    # def test_create_repository_success(self, mock_service_class):
    #     """测试成功创建仓库"""
    #     mock_service = MagicMock()
    #     mock_service_class.return_value = mock_service
        
    #     # 模拟创建的仓库
    #     mock_repo = GitRepository(
    #         id=1,
    #         owner=self.user,
    #         repo_name='abc123-assets',
    #         gitea_repo_id=123,
    #         deploy_key_private='private_key_content',
    #         deploy_key_public='public_key_content',
    #         created_with_template=True
    #     )
    #     mock_service.create_user_repository.return_value = mock_repo
        
    #     url = reverse('git-repository-list')
    #     data = {'template': True}
    #     response = self.client.post(url, data, format='json')
        
    #     assert response.status_code == status.HTTP_201_CREATED
    #     mock_service.create_user_repository.assert_called_once_with(
    #         user=self.user,
    #         use_template=True
    #     )
    
    # @patch('project.apps.git_repository.views.PlatformGitService')
    # def test_create_repository_failure(self, mock_service_class):
    #     """测试创建仓库失败"""
    #     mock_service = MagicMock()
    #     mock_service_class.return_value = mock_service
        
    #     mock_service.create_user_repository.side_effect = GitServiceException('创建失败')
        
    #     url = reverse('git-repository-list')
    #     data = {'template': True}
    #     response = self.client.post(url, data, format='json')
        
    #     assert response.status_code == status.HTTP_400_BAD_REQUEST
    #     assert 'error' in response.data
    
    def test_create_repository_invalid_data(self):
        """测试创建仓库时的无效数据"""
        url = reverse('git-repository-list')
        data = {}  # 缺少 template 字段
        response = self.client.post(url, data, format='json')
        
        # 应该使用默认值 True
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
    
    def test_unauthenticated_access(self):
        """测试未认证访问"""
        self.client.force_authenticate(user=None)
        
        url = reverse('git-repository-list')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestGitSyncAPI:
    """Git 同步 API 测试"""
    
    def setup_method(self):
        """测试设置"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    @patch('project.apps.git_repository.views.PlatformGitService')
    def test_trigger_sync_success(self, mock_service_class):
        """测试成功触发同步"""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        
        mock_service.sync_repository.return_value = {
            'status': 'success',
            'message': '同步成功',
            'synced_at': '2024-01-01T10:00:00Z'
        }
        
        url = reverse('git-sync')
        response = self.client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        mock_service.sync_repository.assert_called_once_with(self.user)
    
    @patch('project.apps.git_repository.views.PlatformGitService')
    def test_trigger_sync_failure(self, mock_service_class):
        """测试同步失败"""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        
        mock_service.sync_repository.side_effect = GitServiceException('未启用 Git 功能')
        
        url = reverse('git-sync')
        response = self.client.post(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
    
    def test_get_sync_status_no_repository(self):
        """测试获取同步状态 - 无仓库"""
        url = reverse('git-sync-status')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_sync_status_success(self):
        """测试获取同步状态 - 成功"""
        repo = GitRepository.objects.create(
            owner=self.user,
            repo_name='abc123-assets',
            gitea_repo_id=123,
            deploy_key_private='private_key_content',
            deploy_key_public='public_key_content',
            sync_status='success'
        )
        
        url = reverse('git-sync-status')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'


@pytest.mark.django_db  
class TestWebhookAPI:
    """Webhook API 测试"""
    
    def setup_method(self):
        """测试设置"""
        self.client = APIClient()
        # Webhook 不需要认证
    
    @patch('project.apps.git_repository.views.PlatformGitService')
    @patch('project.apps.git_repository.views.GitWebhookView._verify_webhook_signature')
    def test_webhook_success(self, mock_verify, mock_service_class):
        """测试 Webhook 成功处理"""
        mock_verify.return_value = True
        
        # 创建用户和仓库用于测试
        user = User.objects.create_user(username='testuser', password='testpass')
        GitRepository.objects.create(
            owner=user,
            repo_name='abc123-assets',
            gitea_repo_id=123,
            deploy_key_private='private_key_content',
            deploy_key_public='public_key_content'
        )
        
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.sync_repository.return_value = {'status': 'success'}
        
        webhook_data = {
            'ref': 'refs/heads/main',
            'repository': {
                'name': 'abc123-assets'
            },
            'pusher': {
                'username': 'testuser'
            },
            'commits': []
        }
        
        url = reverse('git-webhook')
        response = self.client.post(url, webhook_data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        mock_service.sync_repository.assert_called_once()
    
    @patch('project.apps.git_repository.views.GitWebhookView._verify_webhook_signature')
    def test_webhook_invalid_signature(self, mock_verify):
        """测试 Webhook 签名验证失败"""
        mock_verify.return_value = False
        
        url = reverse('git-webhook')
        response = self.client.post(url, {}, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Invalid signature' in response.data['error']

