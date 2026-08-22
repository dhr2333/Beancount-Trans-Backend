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
        instance = FavaInstance.objects.create(
            owner=user,
            status='running',
            container_id='test-container-id',
            container_name='test-container-name'
        )

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.ensure_running.return_value = instance

        response = self.client.get(
            '/api/fava/',
            **self._get_auth_headers(user)
        )

        assert response.status_code == 302
        assert response['Location'] == f'/{instance.uuid}/'
        mock_manager.ensure_running.assert_called_once_with(user, touch_last_accessed=True)

    @patch('project.apps.fava_instances.views.FavaContainerManager')
    def test_get_start_container_failed(self, mock_manager_class, user):
        """测试获取实例 - 启动容器失败"""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.ensure_running.side_effect = Exception('Container start failed')

        response = self.client.get(
            '/api/fava/',
            **self._get_auth_headers(user)
        )

        assert response.status_code == 500
        assert 'error' in response.data

    @patch('project.apps.fava_instances.views.FavaContainerManager')
    def test_get_first_time_user(self, mock_manager_class, user):
        """测试获取实例 - 首次用户，无旧实例"""
        instance = FavaInstance(
            owner=user,
            status='running',
            container_id='new-container-id',
            container_name='new-container-name',
        )
        instance.save()

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.ensure_running.return_value = instance

        response = self.client.get(
            '/api/fava/',
            **self._get_auth_headers(user)
        )

        assert response.status_code == 302
        assert response['Location'] == f'/{instance.uuid}/'
        mock_manager.ensure_running.assert_called_once_with(user, touch_last_accessed=True)
