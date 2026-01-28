"""
Fava 实例测试 fixtures

提供可复用的测试数据和工具函数。
注意：pytest 会自动继承根目录的 conftest.py 中的 fixtures（如清理功能）。
"""
import pytest
from unittest.mock import Mock, MagicMock
from django.contrib.auth import get_user_model
from project.apps.fava_instances.models import FavaInstance

User = get_user_model()


@pytest.fixture
def user():
    """创建测试用户"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def other_user():
    """创建另一个测试用户（用于权限测试）"""
    return User.objects.create_user(
        username='otheruser',
        email='other@example.com',
        password='testpass123'
    )


@pytest.fixture
def mock_docker_client():
    """Mock Docker 客户端"""
    client = MagicMock()
    return client


@pytest.fixture
def mock_container():
    """Mock Docker 容器对象"""
    container = MagicMock()
    container.id = 'test-container-id'
    container.name = 'test-container-name'
    container.status = 'running'
    container.reload = MagicMock()
    container.stop = MagicMock()
    container.remove = MagicMock()
    return container

