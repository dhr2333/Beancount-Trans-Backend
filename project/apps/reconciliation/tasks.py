"""对账模块的异步任务。"""
from celery import shared_task

from project.apps.reconciliation.services.recurring_task_service import RecurringTaskService


@shared_task
def generate_due_recurring_tasks():
    """扫描到期的循环待办定义并生成实例（Celery beat 每小时执行）。"""
    return RecurringTaskService.generate_due()
