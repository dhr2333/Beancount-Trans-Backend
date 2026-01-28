"""
FavaRedirectView 视图测试
"""
import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from project.apps.fava_instances.models import FavaInstance


@pytest.mark.django_db
class TestFavaRedirectView:
    """FavaRedirectView 视图测试"""

    def setup_method(self):
        """设置测试环境"""
        self.client = APIClient()

    def _get_auth_headers(self, user):
        """获取认证头"""
        refresh = RefreshToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    @patch('project.apps.fava_instances.views.FavaContainerManager')
    def test_get_existing_container_running(self, mock_manager_class, user):
        """测试获取实例 - 容器存在且运行正常"""
        # 创建运行中的实例
        instance = FavaInstance.objects.create(
            owner=user,
            status='running',
            container_id='test-container-id',
            container_name='test-container-name'
        )
        
        # Mock manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.verify_and_cleanup_instance.return_value = True
        
        response = self.client.get(
            '/api/fava/',
            **self._get_auth_headers(user)
        )
        
        assert response.status_code == 302
        assert response['Location'] == f'/{instance.uuid}/'
        mock_manager.verify_and_cleanup_instance.assert_called_once_with(instance)

    @patch('project.apps.fava_instances.views.FavaContainerManager')
    @patch('project.utils.file.BeanFileManager')
    def test_get_container_not_exists_create_new(self, mock_bean_manager, mock_manager_class, user):
        """测试获取实例 - 容器不存在，创建新实例"""
        # 创建运行中的实例（但容器不存在）
        old_instance = FavaInstance.objects.create(
            owner=user,
            status='running',
            container_id='old-container-id',
            container_name='old-container-name'
        )
        
        # Mock manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.verify_and_cleanup_instance.return_value = False  # 容器不存在
        mock_manager.cleanup_user_containers.return_value = 1
        mock_manager.start_container.return_value = ('new-container-id', 'new-container-name')
        
        # Mock BeanFileManager
        mock_bean_manager.get_user_assets_path.return_value = '/path/to/assets'
        
        with patch('project.apps.fava_instances.views.settings') as mock_settings:
            mock_settings.ASSETS_HOST_PATH = '/host/assets'
            
            response = self.client.get(
                '/api/fava/',
                **self._get_auth_headers(user)
            )
        
        assert response.status_code == 302
        
        # 验证新实例已创建
        new_instance = FavaInstance.objects.filter(owner=user, status='running').exclude(uuid=old_instance.uuid).first()
        assert new_instance is not None
        assert new_instance.container_id == 'new-container-id'
        assert new_instance.container_name == 'new-container-name'

    @patch('project.apps.fava_instances.views.FavaContainerManager')
    @patch('project.utils.file.BeanFileManager')
    def test_get_start_container_failed(self, mock_bean_manager, mock_manager_class, user):
        """测试获取实例 - 启动容器失败"""
        # Mock manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.cleanup_user_containers.return_value = 0
        mock_manager.start_container.side_effect = Exception('Container start failed')
        
        # Mock BeanFileManager
        mock_bean_manager.get_user_assets_path.return_value = '/path/to/assets'
        
        with patch('project.apps.fava_instances.views.settings') as mock_settings:
            mock_settings.ASSETS_HOST_PATH = '/host/assets'
            
            response = self.client.get(
                '/api/fava/',
                **self._get_auth_headers(user)
            )
        
        assert response.status_code == 500
        assert 'error' in response.data
        
        # 验证失败实例已清理
        failed_instance = FavaInstance.objects.filter(owner=user, status='error').first()
        assert failed_instance is not None
        assert failed_instance.container_id == ''
        assert failed_instance.container_name == ''

    @patch('project.apps.fava_instances.views.FavaContainerManager')
    def test_get_cleanup_old_instances(self, mock_manager_class, user):
        """测试获取实例 - 清理多个旧实例"""
        # 创建多个旧实例（不同状态）
        FavaInstance.objects.create(
            owner=user,
            status='starting',
            container_id='container-1',
            container_name='name-1'
        )
        FavaInstance.objects.create(
            owner=user,
            status='error',
            container_id='container-2',
            container_name='name-2'
        )
        
        # Mock manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.cleanup_user_containers.return_value = 2
        mock_manager.start_container.return_value = ('new-container-id', 'new-container-name')
        
        with patch('project.utils.file.BeanFileManager') as mock_bean_manager, \
             patch('project.apps.fava_instances.views.settings') as mock_settings:
            mock_bean_manager.get_user_assets_path.return_value = '/path/to/assets'
            mock_settings.ASSETS_HOST_PATH = '/host/assets'
            
            response = self.client.get(
                '/api/fava/',
                **self._get_auth_headers(user)
            )
        
        assert response.status_code == 302
        mock_manager.cleanup_user_containers.assert_called_once_with(user)

    @patch('project.apps.fava_instances.views.FavaContainerManager')
    @patch('project.utils.file.BeanFileManager')
    def test_get_first_time_user(self, mock_bean_manager, mock_manager_class, user):
        """测试获取实例 - 首次用户，无旧实例"""
        # Mock manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.cleanup_user_containers.return_value = 0
        mock_manager.start_container.return_value = ('new-container-id', 'new-container-name')
        
        # Mock BeanFileManager
        mock_bean_manager.get_user_assets_path.return_value = '/path/to/assets'
        
        with patch('project.apps.fava_instances.views.settings') as mock_settings:
            mock_settings.ASSETS_HOST_PATH = '/host/assets'
            
            response = self.client.get(
                '/api/fava/',
                **self._get_auth_headers(user)
            )
        
        assert response.status_code == 302
        
        # 验证新实例已创建
        instance = FavaInstance.objects.filter(owner=user, status='running').first()
        assert instance is not None
        assert instance.container_id == 'new-container-id'
        assert instance.container_name == 'new-container-name'

    @patch('project.apps.fava_instances.views.FavaContainerManager')
    @patch('project.utils.file.BeanFileManager')
    def test_get_cleanup_failed_instance(self, mock_bean_manager, mock_manager_class, user):
        """测试获取实例 - 清理失败实例时出错"""
        # 创建失败状态的实例
        FavaInstance.objects.create(
            owner=user,
            status='error',
            container_id='failed-container',
            container_name='failed-name'
        )
        
        # Mock manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.cleanup_user_containers.return_value = 1
        mock_manager.start_container.return_value = ('new-container-id', 'new-container-name')
        
        # Mock BeanFileManager
        mock_bean_manager.get_user_assets_path.return_value = '/path/to/assets'
        
        with patch('project.apps.fava_instances.views.settings') as mock_settings:
            mock_settings.ASSETS_HOST_PATH = '/host/assets'
            
            response = self.client.get(
                '/api/fava/',
                **self._get_auth_headers(user)
            )
        
        assert response.status_code == 302
        mock_manager.cleanup_user_containers.assert_called_once_with(user)

