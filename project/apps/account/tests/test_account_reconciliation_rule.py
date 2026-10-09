"""账户对账周期规则（reconciliation_rule）测试"""
import pytest

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from project.apps.account.models import Account
from project.apps.reconciliation.models import ScheduledTask

User = get_user_model()


@pytest.fixture
def owner():
    """创建测试用户"""
    return User.objects.create_user(
        username='ruleowner', email='ruleowner@example.com', password='pass12345'
    )


def _pending_reconciliation_tasks(account):
    """返回账户下 pending 的对账待办"""
    content_type = ContentType.objects.get_for_model(Account)
    return ScheduledTask.objects.filter(
        task_type='reconciliation',
        content_type=content_type,
        object_id=account.id,
        status='pending',
    )


@pytest.mark.django_db
class TestAccountReconciliationRule:
    """对账周期规则：校验、首建待办、清空取消"""

    def test_clean_accepts_valid_rule(self, owner):
        account = Account(
            account='Assets:Savings:Bank:ICBC',
            owner=owner,
            reconciliation_rule='every month on the last',
        )
        # 合法规则不抛异常
        account.clean()

    def test_clean_rejects_invalid_rule(self, owner):
        account = Account(
            account='Assets:Savings:Bank:ICBC',
            owner=owner,
            reconciliation_rule='every foo',
        )
        with pytest.raises(ValidationError):
            account.clean()

    def test_new_account_with_rule_creates_pending_task(self, owner):
        account = Account.objects.create(
            account='Assets:Savings:Bank:ICBC',
            owner=owner,
            reconciliation_rule='every 1 months',
        )
        assert _pending_reconciliation_tasks(account).count() == 1

    def test_new_account_without_rule_creates_no_task(self, owner):
        account = Account.objects.create(
            account='Assets:Savings:Bank:CMB',
            owner=owner,
        )
        assert _pending_reconciliation_tasks(account).count() == 0

    def test_clear_rule_via_api_cancels_pending_tasks(self, owner):
        account = Account.objects.create(
            account='Assets:Savings:Web:AliPay',
            owner=owner,
            reconciliation_rule='every 1 months',
        )
        assert _pending_reconciliation_tasks(account).count() == 1

        client = APIClient()
        client.force_authenticate(user=owner)
        resp = client.patch(
            f'/api/account/{account.id}/',
            {'reconciliation_rule': ''},
            format='json',
        )
        assert resp.status_code == 200, resp.data
        assert _pending_reconciliation_tasks(account).count() == 0

    def test_invalid_rule_via_api_rejected(self, owner):
        client = APIClient()
        client.force_authenticate(user=owner)
        resp = client.post(
            '/api/account/',
            {'account': 'Assets:Savings:Bank:ABC', 'reconciliation_rule': 'every foo'},
            format='json',
        )
        assert resp.status_code == 400
        assert not Account.objects.filter(owner=owner, account='Assets:Savings:Bank:ABC').exists()
