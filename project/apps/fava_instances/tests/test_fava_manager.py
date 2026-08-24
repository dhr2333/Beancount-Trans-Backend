"""
FavaContainerManager 服务测试
"""
import pytest
from unittest.mock import patch, MagicMock
import docker.errors
from project.apps.fava_instances.services.fava_manager import FavaContainerManager
from project.apps.fava_instances.models import FavaInstance


@pytest.mark.django_db
class TestFavaContainerManager:
    """FavaContainerManager 服务测试"""

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_check_container_exists_success(self, mock_docker_from_env, mock_docker_client, mock_container):
        """测试检查容器存在 - 容器存在"""
        mock_docker_from_env.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_container
        
        manager = FavaContainerManager()
        result = manager.check_container_exists('test-container-id')
        
        assert result is True
        mock_docker_client.containers.get.assert_called_once_with('test-container-id')
        mock_container.reload.assert_called_once()

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_check_container_exists_not_found(self, mock_docker_from_env, mock_docker_client):
        """测试检查容器存在 - 容器不存在"""
        mock_docker_from_env.return_value = mock_docker_client
        mock_docker_client.containers.get.side_effect = docker.errors.NotFound('Container not found')
        
        manager = FavaContainerManager()
        result = manager.check_container_exists('non-existent-container')
        
        assert result is False

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_check_container_exists_empty_id(self, mock_docker_from_env):
        """测试检查容器存在 - container_id 为空"""
        mock_docker_from_env.return_value = MagicMock()
        
        manager = FavaContainerManager()
        result = manager.check_container_exists('')
        
        assert result is False

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_check_container_exists_exception(self, mock_docker_from_env, mock_docker_client):
        """测试检查容器存在 - Docker 异常"""
        mock_docker_from_env.return_value = mock_docker_client
        mock_docker_client.containers.get.side_effect = Exception('Docker error')
        
        manager = FavaContainerManager()
        result = manager.check_container_exists('test-container-id')
        
        assert result is False

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_verify_and_cleanup_instance_container_exists(self, mock_docker_from_env, mock_docker_client, mock_container, user):
        """测试验证并清理实例 - 容器存在"""
        mock_docker_from_env.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_container
        
        instance = FavaInstance.objects.create(
            owner=user,
            status='running',
            container_id='test-container-id',
            container_name='test-container-name'
        )
        
        manager = FavaContainerManager()
        result = manager.verify_and_cleanup_instance(instance)
        
        assert result is True
        instance.refresh_from_db()
        assert instance.container_id == 'test-container-id'  # 未清理
        assert instance.status == 'running'

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_verify_and_cleanup_instance_container_not_exists(self, mock_docker_from_env, mock_docker_client, user):
        """测试验证并清理实例 - 容器不存在"""
        mock_docker_from_env.return_value = mock_docker_client
        mock_docker_client.containers.get.side_effect = docker.errors.NotFound('Container not found')
        
        instance = FavaInstance.objects.create(
            owner=user,
            status='running',
            container_id='non-existent-container',
            container_name='test-container-name'
        )
        
        manager = FavaContainerManager()
        result = manager.verify_and_cleanup_instance(instance)
        
        assert result is False
        instance.refresh_from_db()
        assert instance.container_id == ''  # 已清理
        assert instance.container_name == ''
        assert instance.status == 'stopped'

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_verify_and_cleanup_instance_no_container_id(self, mock_docker_from_env, user):
        """测试验证并清理实例 - 没有 container_id"""
        mock_docker_from_env.return_value = MagicMock()
        
        instance = FavaInstance.objects.create(
            owner=user,
            status='running',
            container_id='',
            container_name=''
        )
        
        manager = FavaContainerManager()
        result = manager.verify_and_cleanup_instance(instance)
        
        assert result is False
        instance.refresh_from_db()
        assert instance.status == 'stopped'

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_cleanup_user_containers(self, mock_docker_from_env, mock_docker_client, mock_container, user, other_user):
        """测试清理用户容器 - 清理当前用户的所有旧实例"""
        mock_docker_from_env.return_value = mock_docker_client
        
        # 创建当前用户的多个旧实例（不同状态）
        instance1 = FavaInstance.objects.create(
            owner=user,
            status='running',
            container_id='container-1',
            container_name='container-name-1'
        )
        instance2 = FavaInstance.objects.create(
            owner=user,
            status='starting',
            container_id='container-2',
            container_name='container-name-2'
        )
        instance3 = FavaInstance.objects.create(
            owner=user,
            status='error',
            container_id='container-3',
            container_name='container-name-3'
        )
        
        # 创建其他用户的实例（不应被清理）
        other_instance = FavaInstance.objects.create(
            owner=other_user,
            status='running',
            container_id='other-container',
            container_name='other-container-name'
        )
        
        # Mock 容器存在性检查
        def mock_get(container_id):
            if container_id == 'container-1':
                return mock_container
            elif container_id == 'container-2':
                raise docker.errors.NotFound('Container not found')
            elif container_id == 'container-3':
                return mock_container
            return MagicMock()
        
        mock_docker_client.containers.get.side_effect = mock_get
        
        manager = FavaContainerManager()
        cleaned_count = manager.cleanup_user_containers(user)
        
        assert cleaned_count == 3
        
        # 验证当前用户的实例都被清理
        instance1.refresh_from_db()
        instance2.refresh_from_db()
        instance3.refresh_from_db()
        assert instance1.container_id == ''
        assert instance1.status == 'stopped'
        assert instance2.container_id == ''
        assert instance2.status == 'stopped'
        assert instance3.container_id == ''
        assert instance3.status == 'stopped'
        
        # 验证其他用户的实例未被清理
        other_instance.refresh_from_db()
        assert other_instance.container_id == 'other-container'
        assert other_instance.status == 'running'

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_cleanup_user_containers_no_instances(self, mock_docker_from_env, mock_docker_client, user):
        """测试清理用户容器 - 没有旧实例"""
        mock_docker_from_env.return_value = mock_docker_client
        
        manager = FavaContainerManager()
        cleaned_count = manager.cleanup_user_containers(user)
        
        assert cleaned_count == 0

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_stop_container_success(self, mock_docker_from_env, mock_docker_client, mock_container):
        """测试停止容器 - 成功"""
        mock_docker_from_env.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_container
        
        manager = FavaContainerManager()
        result = manager.stop_container('test-container-id')
        
        assert result is True
        mock_container.stop.assert_called_once_with(timeout=5)
        mock_container.remove.assert_called_once()

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_stop_container_not_found(self, mock_docker_from_env, mock_docker_client):
        """测试停止容器 - 容器不存在"""
        mock_docker_from_env.return_value = mock_docker_client
        mock_docker_client.containers.get.side_effect = docker.errors.NotFound('Container not found')
        
        manager = FavaContainerManager()
        result = manager.stop_container('non-existent-container')
        
        assert result is False

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_stop_container_empty_id(self, mock_docker_from_env):
        """测试停止容器 - container_id 为空"""
        mock_docker_from_env.return_value = MagicMock()
        
        manager = FavaContainerManager()
        result = manager.stop_container('')
        
        assert result is False

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_stop_container_exception(self, mock_docker_from_env, mock_docker_client, mock_container):
        """测试停止容器 - 异常处理"""
        mock_docker_from_env.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_container
        mock_container.stop.side_effect = Exception('Stop failed')
        
        manager = FavaContainerManager()
        result = manager.stop_container('test-container-id')
        
        assert result is False

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_ensure_running_returns_existing(self, mock_docker_from_env, mock_docker_client, mock_container, user):
        """已有健康容器时直接返回，不刷新 last_accessed"""
        from datetime import timedelta
        from django.utils import timezone

        mock_docker_from_env.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_container

        instance = FavaInstance.objects.create(
            owner=user,
            status='running',
            container_id='test-container-id',
            container_name='test-container-name',
        )
        FavaInstance.objects.filter(pk=instance.pk).update(
            last_accessed=timezone.now() - timedelta(hours=1)
        )
        instance.refresh_from_db()
        original_accessed = instance.last_accessed

        manager = FavaContainerManager()
        result = manager.ensure_running(user, touch_last_accessed=False)

        assert result.uuid == instance.uuid
        instance.refresh_from_db()
        assert instance.last_accessed == original_accessed

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_ensure_running_touch_last_accessed(self, mock_docker_from_env, mock_docker_client, mock_container, user):
        """打开 Fava 时刷新 last_accessed"""
        from datetime import timedelta
        from django.utils import timezone

        mock_docker_from_env.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_container

        instance = FavaInstance.objects.create(
            owner=user,
            status='running',
            container_id='test-container-id',
            container_name='test-container-name',
        )
        FavaInstance.objects.filter(pk=instance.pk).update(
            last_accessed=timezone.now() - timedelta(hours=1)
        )
        instance.refresh_from_db()
        original_accessed = instance.last_accessed

        manager = FavaContainerManager()
        manager.ensure_running(user, touch_last_accessed=True)

        instance.refresh_from_db()
        assert instance.last_accessed > original_accessed

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    @patch('project.utils.file.BeanFileManager')
    def test_ensure_running_starts_new(self, mock_bean_manager, mock_docker_from_env, mock_docker_client, user):
        """无运行实例时启动新容器"""
        mock_docker_from_env.return_value = mock_docker_client
        mock_bean_manager.get_user_assets_path.return_value = '/path/to/assets'

        manager = FavaContainerManager()
        manager.start_container = MagicMock(return_value=('new-id', 'new-name'))

        result = manager.ensure_running(user)

        assert result.status == 'running'
        assert result.container_id == 'new-id'
        assert result.container_name == 'new-name'
        manager.start_container.assert_called_once()

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    @patch('project.utils.file.BeanFileManager')
    def test_ensure_running_start_failed(self, mock_bean_manager, mock_docker_from_env, mock_docker_client, user):
        """启动失败时实例标记为 error"""
        mock_docker_from_env.return_value = mock_docker_client
        mock_bean_manager.get_user_assets_path.return_value = '/path/to/assets'

        manager = FavaContainerManager()
        manager.start_container = MagicMock(side_effect=Exception('Container start failed'))

        with pytest.raises(Exception, match='Container start failed'):
            manager.ensure_running(user)

        failed = FavaInstance.objects.filter(owner=user, status='error').first()
        assert failed is not None
        assert failed.container_id == ''

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_ensure_running_static_mode(self, mock_docker_from_env, user):
        """静态模式不创建容器"""
        from django.test import override_settings

        mock_docker_from_env.return_value = MagicMock()
        manager = FavaContainerManager()
        with override_settings(FAVA_DEPLOY_MODE='static'):
            assert manager.ensure_running(user) is None
        assert FavaInstance.objects.filter(owner=user).count() == 0

    @patch('project.apps.fava_instances.services.fava_manager.docker.from_env')
    def test_ensure_running_waits_for_starting(self, mock_docker_from_env, mock_docker_client, mock_container, user):
        """已有 starting 实例时等待其变为 running"""
        mock_docker_from_env.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_container

        instance = FavaInstance.objects.create(
            owner=user,
            status='starting',
            container_id='starting-id',
            container_name='starting-name',
        )

        def wait(inst, timeout=10, interval=0.5):
            inst.status = 'running'
            inst.save(update_fields=['status'])
            return inst

        manager = FavaContainerManager()
        manager._wait_for_running = wait
        result = manager.ensure_running(user)

        assert result.uuid == instance.uuid
        instance.refresh_from_db()
        assert instance.status == 'running'
        assert instance.container_id == 'starting-id'

