"""
对账模块测试 fixtures

提供可复用的测试数据和工具函数。
注意：pytest 会自动继承根目录的 conftest.py 中的 fixtures（如清理功能）。
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from project.apps.account.models import Account
from project.apps.reconciliation.models import ScheduledTask, CycleUnit

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
def account(user):
    """创建测试账户（不带对账周期配置）"""
    return Account.objects.create(
        account='Assets:Savings:Bank:ICBC',
        owner=user
    )


@pytest.fixture
def account_with_cycle(user):
    """创建带对账周期的账户"""
    return Account.objects.create(
        account='Assets:Savings:Web:AliPay',
        owner=user,
        reconciliation_cycle_unit=CycleUnit.MONTHS,
        reconciliation_cycle_interval=1
    )


@pytest.fixture
def account_with_weekly_cycle(user):
    """创建每周对账周期的账户"""
    return Account.objects.create(
        account='Assets:Savings:Web:WechatPay',
        owner=user,
        reconciliation_cycle_unit=CycleUnit.WEEKS,
        reconciliation_cycle_interval=2
    )


@pytest.fixture
def scheduled_task_pending(user, account):
    """创建待执行的待办任务"""
    content_type = ContentType.objects.get_for_model(Account)
    return ScheduledTask.objects.create(
        task_type='reconciliation',
        content_type=content_type,
        object_id=account.id,
        scheduled_date=date.today(),
        status='pending'
    )


@pytest.fixture
def scheduled_task_completed(user, account):
    """创建已完成的待办任务"""
    content_type = ContentType.objects.get_for_model(Account)
    return ScheduledTask.objects.create(
        task_type='reconciliation',
        content_type=content_type,
        object_id=account.id,
        scheduled_date=date.today() - timedelta(days=5),
        completed_date=date.today() - timedelta(days=3),
        status='completed'
    )


@pytest.fixture
def scheduled_task_cancelled(user, account):
    """创建已取消的待办任务"""
    content_type = ContentType.objects.get_for_model(Account)
    return ScheduledTask.objects.create(
        task_type='reconciliation',
        content_type=content_type,
        object_id=account.id,
        scheduled_date=date.today(),
        status='cancelled'
    )


@pytest.fixture
def scheduled_task_overdue(user, account):
    """创建逾期的待办任务（scheduled_date < today 且 status=pending）"""
    content_type = ContentType.objects.get_for_model(Account)
    return ScheduledTask.objects.create(
        task_type='reconciliation',
        content_type=content_type,
        object_id=account.id,
        scheduled_date=date.today() - timedelta(days=3),
        status='pending'
    )


@pytest.fixture
def scheduled_task_future(user, account):
    """创建未来的待办任务（scheduled_date > today）"""
    content_type = ContentType.objects.get_for_model(Account)
    return ScheduledTask.objects.create(
        task_type='reconciliation',
        content_type=content_type,
        object_id=account.id,
        scheduled_date=date.today() + timedelta(days=5),
        status='pending'
    )


@pytest.fixture
def mock_bean_file_manager():
    """Mock BeanFileManager"""
    with patch('project.apps.reconciliation.services.balance_calculation_service.BeanFileManager') as mock:
        yield mock


@pytest.fixture
def mock_bean_file_path(tmp_path, user):
    """创建临时 bean 文件路径并 mock BeanFileManager.get_main_bean_path"""
    bean_file = tmp_path / f"{user.username}_main.bean"
    bean_file.write_text("", encoding='utf-8')
    
    with patch('project.apps.reconciliation.services.balance_calculation_service.BeanFileManager.get_main_bean_path') as mock_path:
        mock_path.return_value = str(bean_file)
        yield str(bean_file)


@pytest.fixture
def mock_bean_content():
    """Mock Beancount 账本内容（多币种场景）"""
    return """
2025-01-01 open Assets:Savings:Bank:ICBC CNY
2025-01-01 open Assets:Savings:Web:AliPay CNY
2025-01-01 open Assets:Savings:Web:AliPay COIN
2025-01-01 open Income:Investment:Interest CNY

2025-01-15 * "测试交易"
    Assets:Savings:Bank:ICBC 1000.00 CNY
    Income:Salary -1000.00 CNY

2025-01-20 * "测试交易2"
    Assets:Savings:Web:AliPay 500.00 CNY
    Assets:Savings:Web:AliPay 100.00 COIN
    Income:Investment:Interest -500.00 CNY
    Income:Investment:Interest -100.00 COIN
"""


@pytest.fixture
def mock_beancount_loader(mock_bean_content, mock_bean_file_path):
    """Mock beancount.loader.load_file"""
    from beancount import loader
    from io import StringIO
    
    # 创建临时文件并写入内容
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bean', delete=False, encoding='utf-8') as f:
        f.write(mock_bean_content)
        temp_path = f.name
    
    try:
        # 加载真实的 beancount 文件
        entries, errors, options = loader.load_file(temp_path)
        
        with patch('project.apps.reconciliation.services.balance_calculation_service.loader.load_file') as mock_loader:
            mock_loader.return_value = (entries, errors, options)
            yield mock_loader
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@pytest.fixture
def mock_reconciliation_bean_path(tmp_path, user):
    """Mock reconciliation.bean 文件路径"""
    reconciliation_file = tmp_path / f"{user.username}_reconciliation.bean"
    
    with patch('project.apps.reconciliation.services.reconciliation_service.BeanFileManager.get_reconciliation_bean_path') as mock_path:
        mock_path.return_value = str(reconciliation_file)
        yield str(reconciliation_file)


@pytest.fixture
def mock_ensure_reconciliation_included():
    """Mock ensure_reconciliation_bean_included"""
    with patch('project.apps.reconciliation.services.reconciliation_service.BeanFileManager.ensure_reconciliation_bean_included') as mock:
        yield mock

