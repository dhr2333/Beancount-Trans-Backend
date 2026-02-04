"""
解析模块测试 fixtures

提供可复用的测试数据和工具函数。
"""
import pytest
import time
import os
import shutil
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from project.apps.file_manager.models import File, Directory
from project.apps.translate.models import ParseFile, FormatConfig
from project.apps.reconciliation.models import ScheduledTask

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
def format_config(user):
    """创建格式配置（审核模式）"""
    return FormatConfig.objects.create(
        owner=user,
        parsing_mode_preference='review'
    )


@pytest.fixture
def format_config_direct_write(user):
    """创建格式配置（直接写入模式）"""
    return FormatConfig.objects.create(
        owner=user,
        parsing_mode_preference='direct_write'
    )


@pytest.fixture
def directory(user):
    """创建测试目录"""
    return Directory.objects.create(
        name='test_dir',
        owner=user
    )


@pytest.fixture
def file_obj(user, directory):
    """创建测试文件"""
    return File.objects.create(
        name='test_file.csv',
        directory=directory,
        storage_name='test_storage_name',
        size=1024,
        owner=user,
        content_type='text/csv'
    )


@pytest.fixture
def parse_file(user, file_obj):
    """创建 ParseFile"""
    return ParseFile.objects.create(
        file=file_obj,
        status='pending_review'
    )


@pytest.fixture
def parse_review_task(user, parse_file):
    """创建解析审核待办任务"""
    content_type = ContentType.objects.get_for_model(ParseFile)
    return ScheduledTask.objects.create(
        task_type='parse_review',
        content_type=content_type,
        object_id=parse_file.file_id,
        status='pending'
    )


@pytest.fixture
def parse_review_task_inactive(user, parse_file):
    """创建未激活的解析审核待办任务"""
    content_type = ContentType.objects.get_for_model(ParseFile)
    return ScheduledTask.objects.create(
        task_type='parse_review',
        content_type=content_type,
        object_id=parse_file.file_id,
        status='inactive'
    )


@pytest.fixture
def parse_review_task_completed(user, parse_file):
    """创建已完成的解析审核待办任务"""
    content_type = ContentType.objects.get_for_model(ParseFile)
    return ScheduledTask.objects.create(
        task_type='parse_review',
        content_type=content_type,
        object_id=parse_file.file_id,
        status='completed'
    )


@pytest.fixture
def mock_parse_result_data():
    """模拟解析结果数据"""
    current_time = time.time()
    return {
        'file_id': 1,
        'formatted_data': [
            {
                'uuid': 'entry-1',
                'formatted': '2025-01-20 * "Test" "Transaction 1"\n    Expenses:Test  100.00 CNY\n    Assets:Test  -100.00 CNY\n',
                'edited_formatted': '2025-01-20 * "Test" "Transaction 1"\n    Expenses:Test  100.00 CNY\n    Assets:Test  -100.00 CNY\n',
                'selected_expense_key': 'Expenses:Test',
                'expense_candidates_with_score': [
                    {'key': 'Expenses:Test', 'score': 0.9}
                ],
                'original_row': {'date': '2025-01-20', 'description': 'Test Transaction 1', 'amount': 100.00}
            },
            {
                'uuid': 'entry-2',
                'formatted': '2025-01-21 * "Test" "Transaction 2"\n    Expenses:Test  200.00 CNY\n    Assets:Test  -200.00 CNY\n',
                'edited_formatted': '2025-01-21 * "Test" "Transaction 2"\n    Expenses:Test  200.00 CNY\n    Assets:Test  -200.00 CNY\n',
                'selected_expense_key': 'Expenses:Test',
                'expense_candidates_with_score': [
                    {'key': 'Expenses:Test', 'score': 0.85}
                ],
                'original_row': {'date': '2025-01-21', 'description': 'Test Transaction 2', 'amount': 200.00}
            }
        ],
        'created_at': current_time,
        'expires_at': current_time + 86400  # 24小时后
    }


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """自动清理测试用户创建的文件
    
    在每个测试结束后，清理 testuser 和 otheruser 在 Assets 目录下创建的文件
    """
    yield  # 测试执行
    
    # 测试结束后清理
    test_usernames = ['testuser', 'otheruser']
    assets_base_path = getattr(settings, 'ASSETS_BASE_PATH', None)
    
    if assets_base_path:
        # 处理 Path 对象
        if hasattr(assets_base_path, '__fspath__'):
            assets_base_path = str(assets_base_path)
        
        for username in test_usernames:
            user_assets_path = os.path.join(assets_base_path, username)
            if os.path.exists(user_assets_path):
                try:
                    shutil.rmtree(user_assets_path)
                except Exception as e:
                    # 如果删除失败，记录警告但不影响测试
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"清理测试文件失败: {user_assets_path}, 错误: {str(e)}")


