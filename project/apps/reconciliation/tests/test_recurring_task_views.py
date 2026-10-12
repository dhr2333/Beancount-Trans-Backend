"""
循环待办定义 API 测试

覆盖 RecurringTaskViewSet 的增删改查/规则预览，以及
ScheduledTaskViewSet.complete 完成循环待办实例的接口。
"""
import pytest
from datetime import date, timedelta
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.contenttypes.models import ContentType

from project.apps.reconciliation.models import RecurringTask, ScheduledTask
from project.apps.reconciliation.services import RecurringTaskService


RECURRING_URL = '/api/reconciliation/recurring-tasks/'
TASKS_URL = '/api/reconciliation/tasks/'


@pytest.mark.django_db
class TestRecurringTaskViewSet:
    """循环待办定义 API 测试"""

    def test_create_definition(self, user):
        """POST /api/reconciliation/recurring-tasks/ 创建定义：rrule 归一化、状态 active

        start_date 取未来日期，避免创建时即时对齐生成待办实例。
        """
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(RECURRING_URL, {
            'rule_text': 'every 3 days',
            'start_date': '2099-01-01',
        }, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['rrule'] == 'FREQ=DAILY;INTERVAL=3'
        assert response.data['start_date'] == '2099-01-01'
        assert response.data['has_pending'] is False

        defn = RecurringTask.objects.get(id=response.data['id'])
        assert defn.user == user
        assert defn.status == 'active'

    def test_create_allows_null_optional_fields(self, user):
        """POST 传 null 的可选字段（start_date/recurrence_basis）应成功并归一化"""
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(RECURRING_URL, {
            'rule_text': 'every month on the last',
            'start_date': None,
            'recurrence_basis': None,
        }, format='json')

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data['start_date'] == date.today().isoformat()
        assert response.data['recurrence_basis'] == 'scheduled'

    def test_create_invalid_rule_returns_400_and_persists_nothing(self, user):
        """POST 无效规则返回 400，且不落库"""
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(RECURRING_URL, {
            'rule_text': 'foo bar',
        }, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '无法识别的循环规则' in str(response.data)
        assert RecurringTask.objects.count() == 0

    def test_create_generate_review_requires_template(self, user):
        """kind=generate_review 且模板为空时返回 400（不做语法校验）"""
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(RECURRING_URL, {
            'rule_text': 'every month',
            'kind': 'generate_review',
        }, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'template' in response.data
        assert RecurringTask.objects.count() == 0

    def test_create_generate_review_with_template_persists(self, user):
        """kind=generate_review + 非空模板：保存成功，模板原样入库"""
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(RECURRING_URL, {
            'rule_text': 'every month',
            'start_date': '2099-01-01',
            'kind': 'generate_review',
            'template': '2099-01-01 * "x" "y"\n    Expenses:Food:Lunch 1.00 CNY\n    Assets:WeChat -1.00 CNY',
        }, format='json')

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data['kind'] == 'generate_review'
        defn = RecurringTask.objects.get(id=response.data['id'])
        assert defn.template.startswith('2099-01-01 * "x"')

    def test_list_only_own_definitions(self, user, other_user):
        """GET 列表仅返回当前用户的定义"""
        mine = RecurringTaskService.create(
            user, 'every 3 days', start_date=date(2026, 1, 1)
        )
        RecurringTaskService.create(
            other_user, 'every 3 days', start_date=date(2026, 1, 1)
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(RECURRING_URL)

        assert response.status_code == status.HTTP_200_OK
        data = response.data.get('results', response.data) if hasattr(response.data, 'get') else response.data
        ids = [item['id'] for item in data]
        assert mine.id in ids
        assert len(ids) == 1

    def test_retrieve_other_user_definition_404(self, user, other_user):
        """用户 A 检索用户 B 的定义返回 404"""
        other = RecurringTaskService.create(
            other_user, 'every 3 days', start_date=date(2026, 1, 1)
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(f'{RECURRING_URL}{other.id}/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_preview_rule_returns_describe_and_occurrences(self, user):
        """POST .../recurring-tasks/preview/ 即时预览规则返回 describe 与 next_occurrences"""
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(f'{RECURRING_URL}preview/', {
            'rule_text': 'every 3 days',
            'start_date': '2026-01-01',
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['describe'] == '每 3 天'
        assert len(response.data['next_occurrences']) == 5

    def test_delete_cancels_pending_instances(self, user):
        """DELETE 定义后其待执行实例变为 cancelled"""
        today = date.today()
        defn = RecurringTaskService.create(
            user, 'every 3 days', start_date=today - timedelta(days=1)
        )
        RecurringTaskService.generate_due(today=today)
        task = ScheduledTask.objects.get(
            task_type='recurring', object_id=defn.id, status='pending'
        )
        task_id = task.id

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.delete(f'{RECURRING_URL}{defn.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not RecurringTask.objects.filter(id=defn.id).exists()

        task = ScheduledTask.objects.get(id=task_id)
        assert task.status == 'cancelled'


@pytest.mark.django_db
class TestScheduledTaskComplete:
    """ScheduledTask 完成循环待办实例接口测试"""

    def test_complete_recurring_instance(self, user):
        """POST /api/reconciliation/tasks/{id}/complete/ 完成循环实例返回 completed/next_date"""
        today = date.today()
        defn = RecurringTaskService.create(
            user, 'every 3 days', start_date=today - timedelta(days=1)
        )
        RecurringTaskService.generate_due(today=today)
        task = ScheduledTask.objects.get(
            task_type='recurring', object_id=defn.id, status='pending'
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(f'{TASKS_URL}{task.id}/complete/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['completed'] == task.id
        assert response.data['next_date'] is not None

        task.refresh_from_db()
        assert task.status == 'completed'

    def test_update_recurring_instance_scheduled_date(self, user):
        """PATCH /api/reconciliation/tasks/{id}/ 允许用户修改循环实例的执行日期"""
        today = date.today()
        defn = RecurringTaskService.create(
            user, 'every 3 days', start_date=today - timedelta(days=1)
        )
        RecurringTaskService.generate_due(today=today)
        task = ScheduledTask.objects.get(
            task_type='recurring', object_id=defn.id, status='pending'
        )
        new_date = today + timedelta(days=5)

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch(f'{TASKS_URL}{task.id}/', {'scheduled_date': new_date.isoformat()})

        assert response.status_code == status.HTTP_200_OK
        task.refresh_from_db()
        assert task.scheduled_date == new_date

    def test_update_recurring_instance_date_postpones_definition(self, user):
        """循环卡片改期到未来：取消旧实例、定义顺延；管理页显示新日期且可编辑"""
        from project.apps.reconciliation.serializers import RecurringTaskSerializer

        today = date.today()
        tomorrow = today + timedelta(days=1)
        defn = RecurringTaskService.create(user, 'every month', start_date=today)
        task = ScheduledTask.objects.get(
            task_type='recurring', object_id=defn.id, status='pending'
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch(
            f'{TASKS_URL}{task.id}/', {'scheduled_date': tomorrow.isoformat()}
        )

        assert response.status_code == status.HTTP_200_OK

        defn.refresh_from_db()
        assert defn.start_date == tomorrow
        assert RecurringTaskService.has_pending(defn) is False

        task.refresh_from_db()
        assert task.status == 'cancelled'

        data = RecurringTaskSerializer(defn).data
        assert data['has_pending'] is False
        assert data['next_run_date'] == tomorrow.isoformat()

    def test_complete_reconciliation_instance_returns_400(self, user, account, scheduled_task_pending):
        """对非循环（reconciliation）实例调用 complete 返回 400"""
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(f'{TASKS_URL}{scheduled_task_pending.id}/complete/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '该待办不是循环待办' in str(response.data)

    def test_list_tasks_filter_recurring_isolation_and_title(self, user, other_user):
        """GET /api/reconciliation/tasks/?task_type=recurring 仅返回本人循环实例且 recurring_label 填充"""
        ct = ContentType.objects.get_for_model(RecurringTask)

        defn = RecurringTaskService.create(
            user, 'every 3 days', start_date=date.today()
        )
        mine = ScheduledTask.objects.create(
            task_type='recurring',
            content_type=ct,
            object_id=defn.id,
            scheduled_date=date.today(),
            status='pending',
        )

        other_defn = RecurringTaskService.create(
            other_user, 'every 3 days', start_date=date.today()
        )
        other = ScheduledTask.objects.create(
            task_type='recurring',
            content_type=ct,
            object_id=other_defn.id,
            scheduled_date=date.today(),
            status='pending',
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(TASKS_URL, {'task_type': 'recurring'})

        assert response.status_code == status.HTTP_200_OK
        data = response.data.get('results', response.data) if hasattr(response.data, 'get') else response.data
        ids = [item['id'] for item in data]
        assert mine.id in ids
        assert other.id not in ids

        row = next(item for item in data if item['id'] == mine.id)
        assert row['recurring_label'] == '每 3 天'
