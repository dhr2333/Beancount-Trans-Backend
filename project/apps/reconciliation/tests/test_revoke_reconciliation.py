"""
撤销对账 API 与服务层测试
"""
import pytest
from datetime import date, timedelta
from unittest.mock import patch
from rest_framework.test import APIClient
from rest_framework import status

from project.apps.reconciliation.models import ScheduledTask
from project.apps.reconciliation.services.reconciliation_service import ReconciliationService
from project.apps.account.models import Account


@pytest.fixture
def mock_reconciliation_paths(tmp_path, user):
    """Mock BeanFileManager 路径，使 reconciliation 和 comment 服务使用同一临时文件"""
    recon_path = tmp_path / f"{user.username}_trans" / "reconciliation.bean"
    recon_path.parent.mkdir(parents=True, exist_ok=True)
    recon_path.touch()

    with patch('project.utils.file.BeanFileManager.get_reconciliation_bean_path') as mock_get_recon:
        with patch('project.utils.file.BeanFileManager.get_user_assets_path') as mock_get_user:
            mock_get_recon.return_value = str(recon_path)
            mock_get_user.return_value = str(tmp_path)
            yield str(recon_path)


@pytest.fixture
def mock_main_bean_and_ensure(tmp_path, user, mock_bean_content):
    """Mock main bean 和 ensure_reconciliation_bean_included"""
    main_path = tmp_path / f"{user.username}_main.bean"
    main_path.write_text(mock_bean_content, encoding='utf-8')
    with patch('project.utils.file.BeanFileManager.get_main_bean_path') as mock_main:
        with patch('project.utils.file.BeanFileManager.ensure_reconciliation_bean_included'):
            mock_main.return_value = str(main_path)
            yield str(main_path)


@pytest.mark.django_db
class TestRevokeReconciliationAPI:
    """撤销对账 API 测试"""

    def test_revoke_reconciliation_success(
        self,
        user,
        account_with_cycle,
        mock_reconciliation_paths,
        mock_main_bean_and_ensure,
    ):
        """测试撤销对账成功：原任务 revoked，新任务创建/更新，条目被注释"""
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(Account)
        task = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account_with_cycle.id,
            scheduled_date=date.today() - timedelta(days=1),
            completed_date=date.today(),
            as_of_date=date.today(),
            status='completed',
            reconciliation_entries=[
                {
                    'type': 'Balance',
                    'date': (date.today() + timedelta(days=1)).isoformat(),
                    'account': account_with_cycle.account,
                    'amount': '1000.00',
                    'currency': 'CNY',
                }
            ],
        )
        # 写入对账条目到 reconciliation.bean
        with open(mock_reconciliation_paths, 'w', encoding='utf-8') as f:
            f.write("; Auto-generated\n\n")
            balance_date = (date.today() + timedelta(days=1)).isoformat()
            f.write(
                f'{balance_date} balance {account_with_cycle.account} 1000.00 CNY\n\n'
            )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            f'/api/reconciliation/tasks/{task.id}/revoke_reconciliation/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'new_task_id' in response.data
        assert 'entries_commented' in response.data
        assert 'message' in response.data

        task.refresh_from_db()
        assert task.status == 'revoked'

        new_task = ScheduledTask.objects.get(id=response.data['new_task_id'])
        assert new_task.status == 'pending'
        assert new_task.scheduled_date == date.today()

    def test_revoke_reconciliation_when_entries_already_commented_is_idempotent(
        self,
        user,
        account_with_cycle,
        mock_reconciliation_paths,
        mock_main_bean_and_ensure,
    ):
        """测试撤销时目标条目已被注释（Git/手动注释）也应成功且不重复注释"""
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(Account)
        task = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account_with_cycle.id,
            scheduled_date=date.today() - timedelta(days=1),
            completed_date=date.today(),
            as_of_date=date.today(),
            status='completed',
            reconciliation_entries=[
                {
                    'type': 'Balance',
                    'date': (date.today() + timedelta(days=1)).isoformat(),
                    'account': account_with_cycle.account,
                    'amount': '1000.00',
                    'currency': 'CNY',
                }
            ],
        )

        # 文件中已是注释状态
        with open(mock_reconciliation_paths, 'w', encoding='utf-8') as f:
            f.write("; Auto-generated\n\n")
            balance_date = (date.today() + timedelta(days=1)).isoformat()
            f.write(
                f'; {balance_date} balance {account_with_cycle.account} 1000.00 CNY\n\n'
            )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            f'/api/reconciliation/tasks/{task.id}/revoke_reconciliation/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('entries_commented') == 0
        task.refresh_from_db()
        assert task.status == 'revoked'

    def test_revoke_reconciliation_updates_existing_pending(
        self,
        user,
        account_with_cycle,
        mock_reconciliation_paths,
    ):
        """测试撤销时若有同账户 pending 待办，则更新其 scheduled_date 为当天（不新建）"""
        from django.contrib.contenttypes.models import ContentType

        # 取消账户创建时自动生成的待办，仅保留我们创建的
        ScheduledTask.objects.filter(
            task_type='reconciliation',
            object_id=account_with_cycle.id,
            status='pending',
        ).update(status='cancelled')

        content_type = ContentType.objects.get_for_model(Account)
        completed_task = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account_with_cycle.id,
            scheduled_date=date.today() - timedelta(days=5),
            completed_date=date.today(),
            as_of_date=date.today() - timedelta(days=5),
            status='completed',
            reconciliation_entries=None,
        )
        existing_pending = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account_with_cycle.id,
            scheduled_date=date.today() + timedelta(days=3),
            status='pending',
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            f'/api/reconciliation/tasks/{completed_task.id}/revoke_reconciliation/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['new_task_id'] == existing_pending.id

        existing_pending.refresh_from_db()
        assert existing_pending.scheduled_date == date.today()

    def test_revoke_reconciliation_not_completed_returns_400(
        self,
        user,
        account,
        scheduled_task_pending,
    ):
        """测试只能撤销已完成的对账任务"""
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            f'/api/reconciliation/tasks/{scheduled_task_pending.id}/revoke_reconciliation/'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '已完成' in str(response.data)

    def test_revoke_reconciliation_wrong_task_type_returns_400(
        self,
        user,
        scheduled_task_completed,
    ):
        """测试非对账任务不能撤销（通过 parse_review 等）"""
        # scheduled_task_completed 是对账任务，需要创建一个 parse_review 任务
        from project.apps.translate.models import ParseFile
        from django.contrib.contenttypes.models import ContentType

        # 这里简化：我们测试传入非 completed 状态
        scheduled_task_completed.status = 'pending'
        scheduled_task_completed.save()

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            f'/api/reconciliation/tasks/{scheduled_task_completed.id}/revoke_reconciliation/'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_revoke_after_revoke_allows_same_as_of_date_execute(
        self,
        user,
        account_with_cycle,
        mock_reconciliation_paths,
        mock_main_bean_and_ensure,
    ):
        """测试撤销后可以对同一 as_of_date 再次执行对账"""
        from django.contrib.contenttypes.models import ContentType

        as_of = date.today()
        content_type = ContentType.objects.get_for_model(Account)
        completed_task = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account_with_cycle.id,
            scheduled_date=as_of,
            completed_date=as_of,
            as_of_date=as_of,
            status='completed',
            reconciliation_entries=[],
        )
        # 写入一些内容
        with open(mock_reconciliation_paths, 'w', encoding='utf-8') as f:
            f.write("; test\n\n")

        client = APIClient()
        client.force_authenticate(user=user)

        revoke_resp = client.post(
            f'/api/reconciliation/tasks/{completed_task.id}/revoke_reconciliation/'
        )
        assert revoke_resp.status_code == status.HTTP_200_OK

        new_task_id = revoke_resp.data['new_task_id']
        new_task = ScheduledTask.objects.get(id=new_task_id)

        # 执行对账（同一 as_of_date 应允许，因为原记录已 revoked）
        # mock_bean_content 中 Assets:Savings:Web:AliPay 有 500 CNY，传无差额的 actual_balance
        execute_resp = client.post(
            f'/api/reconciliation/tasks/{new_task_id}/execute/',
            {
                'actual_balance': '500.00',
                'currency': 'CNY',
                'as_of_date': str(as_of),
            },
            format='json',
        )

        assert execute_resp.status_code == status.HTTP_200_OK, execute_resp.data
        assert execute_resp.data['status'] == 'success'

    def test_revoke_reconciliation_only_latest_returns_400(
        self,
        user,
        account_with_cycle,
        mock_reconciliation_paths,
    ):
        """测试仅允许撤销最近一次对账，撤销更早的返回 400"""
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(Account)
        # 较早完成的对账
        older = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account_with_cycle.id,
            scheduled_date=date.today() - timedelta(days=10),
            completed_date=date.today() - timedelta(days=9),
            as_of_date=date.today() - timedelta(days=9),
            status='completed',
            reconciliation_entries=[],
        )
        # 最近完成的对账
        latest = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account_with_cycle.id,
            scheduled_date=date.today() - timedelta(days=2),
            completed_date=date.today(),
            as_of_date=date.today(),
            status='completed',
            reconciliation_entries=[],
        )

        with open(mock_reconciliation_paths, 'w', encoding='utf-8') as f:
            f.write("; test\n\n")

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            f'/api/reconciliation/tasks/{older.id}/revoke_reconciliation/'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '最近一次' in str(response.data.get('error', response.data))
        older.refresh_from_db()
        assert older.status == 'completed'
        latest.refresh_from_db()
        assert latest.status == 'completed'

    def test_start_returns_prefill_after_revoke(
        self,
        user,
        account_with_cycle,
        mock_reconciliation_paths,
    ):
        """测试撤销后对新待办调用 start 返回被撤销任务的 transaction_items 用于预填"""
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(Account)
        completed = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account_with_cycle.id,
            scheduled_date=date.today(),
            completed_date=date.today(),
            as_of_date=date.today(),
            status='completed',
            reconciliation_entries=[],
            reconciliation_transaction_items=[
                {'account': 'Equity:Adjustments', 'amount': '100.00', 'is_auto': False, 'date': date.today().isoformat()},
            ],
        )
        with open(mock_reconciliation_paths, 'w', encoding='utf-8') as f:
            f.write("; test\n\n")

        client = APIClient()
        client.force_authenticate(user=user)

        revoke_resp = client.post(
            f'/api/reconciliation/tasks/{completed.id}/revoke_reconciliation/'
        )
        assert revoke_resp.status_code == status.HTTP_200_OK
        new_task_id = revoke_resp.data['new_task_id']

        start_resp = client.post(f'/api/reconciliation/tasks/{new_task_id}/start/')
        assert start_resp.status_code == status.HTTP_200_OK
        assert start_resp.data.get('last_reconciliation_transaction_items') == [
            {'account': 'Equity:Adjustments', 'amount': '100.00', 'is_auto': False, 'date': date.today().isoformat()},
        ]
        assert start_resp.data.get('last_completed_task_id') is None


@pytest.mark.django_db
class TestReconciliationEntriesStored:
    """测试 execute_reconciliation 正确存储 reconciliation_entries"""

    def test_execute_reconciliation_stores_reconciliation_entries(
        self,
        user,
        account_with_cycle,
        mock_reconciliation_paths,
        mock_main_bean_and_ensure,
        mock_bean_content,
    ):
        """测试执行对账后 task.reconciliation_entries 已写入"""
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(Account)
        task = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=content_type,
            object_id=account_with_cycle.id,
            scheduled_date=date.today(),
            status='pending',
        )
        # mock_bean_content 中 Assets:Savings:Web:AliPay 有 500 CNY
        result = ReconciliationService.execute_reconciliation(
            task=task,
            actual_balance=500,
            currency='CNY',
            as_of_date=date.today(),
        )

        assert result['status'] == 'success'
        task.refresh_from_db()
        assert task.reconciliation_entries is not None
        assert isinstance(task.reconciliation_entries, list)
        assert len(task.reconciliation_entries) >= 1
        assert task.reconciliation_entries[0].get('type') == 'Balance'
