"""
ScheduledTask 模型测试
"""
import pytest
from datetime import date, timedelta
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from project.apps.reconciliation.models import ScheduledTask
from project.apps.account.models import Account


@pytest.mark.django_db
class TestScheduledTaskModel:
    """ScheduledTask 模型测试"""
    
    def test_create_reconciliation_task(self, user, account):
        """测试创建对账类型待办"""
        content_type = ContentType.objects.get_for_model(Account)
        task = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account.id,
            scheduled_date=date.today(),
            status='pending'
        )
        
        assert task.task_type == 'reconciliation'
        assert task.content_object == account
        assert task.scheduled_date == date.today()
        assert task.status == 'pending'
        assert task.completed_date is None
    
    def test_content_type_and_object_id_relation(self, user, account):
        """测试 content_type 和 object_id 关联账户"""
        content_type = ContentType.objects.get_for_model(Account)
        task = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account.id,
            scheduled_date=date.today()
        )
        
        assert task.content_type == content_type
        assert task.object_id == account.id
        assert task.content_object == account
    
    def test_scheduled_date_and_completed_date_fields(self, user, account):
        """测试 scheduled_date 和 completed_date 字段"""
        content_type = ContentType.objects.get_for_model(Account)
        scheduled = date.today()
        completed = date.today() - timedelta(days=1)
        
        task = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account.id,
            scheduled_date=scheduled,
            completed_date=completed,
            status='completed'
        )
        
        assert task.scheduled_date == scheduled
        assert task.completed_date == completed
    
    def test_status_default_value(self, user, account):
        """测试 status 字段默认值为 'pending'"""
        content_type = ContentType.objects.get_for_model(Account)
        task = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account.id,
            scheduled_date=date.today()
        )
        
        assert task.status == 'pending'
    
    def test_status_choices(self, user, account):
        """测试 status 字段选择（pending, completed, cancelled）"""
        content_type = ContentType.objects.get_for_model(Account)
        
        # 测试 pending
        task1 = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account.id,
            scheduled_date=date.today(),
            status='pending'
        )
        assert task1.status == 'pending'
        assert task1.get_status_display() == '待执行'
        
        # 测试 completed
        task2 = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account.id,
            scheduled_date=date.today(),
            status='completed',
            completed_date=date.today()
        )
        assert task2.status == 'completed'
        assert task2.get_status_display() == '已完成'
        
        # 测试 cancelled
        task3 = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account.id,
            scheduled_date=date.today(),
            status='cancelled'
        )
        assert task3.status == 'cancelled'
        assert task3.get_status_display() == '已取消'
    
    def test_str_method(self, user, account):
        """测试 __str__ 方法返回正确格式"""
        content_type = ContentType.objects.get_for_model(Account)
        task = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account.id,
            scheduled_date=date(2026, 1, 20),
            status='pending'
        )
        
        str_repr = str(task)
        assert '对账' in str_repr
        assert '2026-01-20' in str_repr
        assert '待执行' in str_repr
    
    def test_get_pending_tasks(self, user, account):
        """测试 get_pending_tasks 类方法"""
        content_type = ContentType.objects.get_for_model(Account)
        
        # 创建多个待办
        task1 = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account.id,
            scheduled_date=date.today(),
            status='pending'
        )
        
        task2 = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account.id,
            scheduled_date=date.today() - timedelta(days=1),
            status='pending'
        )
        
        # 创建已完成的待办（不应被查询到）
        task3 = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account.id,
            scheduled_date=date.today(),
            status='completed',
            completed_date=date.today()
        )
        
        # 创建未来的待办（不应被查询到）
        task4 = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account.id,
            scheduled_date=date.today() + timedelta(days=1),
            status='pending'
        )
        
        # 查询待执行的任务
        pending_tasks = ScheduledTask.get_pending_tasks(
            task_type='reconciliation',
            as_of_date=date.today()
        )
        
        assert task1 in pending_tasks
        assert task2 in pending_tasks
        assert task3 not in pending_tasks
        assert task4 not in pending_tasks
    
    def test_get_pending_tasks_with_task_type_filter(self, user, account):
        """测试 get_pending_tasks 按任务类型过滤"""
        content_type = ContentType.objects.get_for_model(Account)
        
        # 创建对账任务
        reconciliation_task = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account.id,
            scheduled_date=date.today(),
            status='pending'
        )
        
        # 创建 AI 反馈任务
        ai_task = ScheduledTask.objects.create(
            task_type='ai_feedback',
            content_type=content_type,
            object_id=account.id,
            scheduled_date=date.today(),
            status='pending'
        )
        
        # 只查询对账任务
        reconciliation_tasks = ScheduledTask.get_pending_tasks(
            task_type='reconciliation',
            as_of_date=date.today()
        )
        
        assert reconciliation_task in reconciliation_tasks
        assert ai_task not in reconciliation_tasks

