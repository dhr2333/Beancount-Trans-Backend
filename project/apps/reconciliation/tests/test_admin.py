import pytest
from datetime import date

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory

from project.apps.account.models import Account
from project.apps.reconciliation.admin import ScheduledTaskAdmin
from project.apps.reconciliation.models import ScheduledTask


User = get_user_model()


@pytest.mark.django_db
class TestScheduledTaskAdminSearch:
    def setup_method(self):
        self.factory = RequestFactory()
        self.admin = ScheduledTaskAdmin(ScheduledTask, AdminSite())

    def test_search_by_username_includes_reconciliation_tasks(self):
        matched_user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='testpass123',
        )
        other_user = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='testpass123',
        )

        account_content_type = ContentType.objects.get_for_model(Account)

        matched_account = Account.objects.create(
            account='Assets:Cash',
            owner=matched_user,
        )
        other_account = Account.objects.create(
            account='Assets:Bank',
            owner=other_user,
        )

        reconciliation_task = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=account_content_type,
            object_id=matched_account.id,
            scheduled_date=date.today(),
            status='pending',
        )
        ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=account_content_type,
            object_id=other_account.id,
            scheduled_date=date.today(),
            status='pending',
        )

        request = self.factory.get('/admin/reconciliation/scheduledtask/', {'q': 'alice'})
        queryset = ScheduledTask.objects.all()

        results, _ = self.admin.get_search_results(request, queryset, 'alice')

        assert set(results.values_list('id', flat=True)) == {reconciliation_task.id}

    def test_search_by_object_id_still_works(self):
        user = User.objects.create_user(
            username='charlie',
            email='charlie@example.com',
            password='testpass123',
        )
        account = Account.objects.create(
            account='Assets:Investments',
            owner=user,
        )
        task = ScheduledTask.objects.create(
            task_type='reconciliation',
            content_type=ContentType.objects.get_for_model(Account),
            object_id=account.id,
            scheduled_date=date.today(),
            status='pending',
        )

        request = self.factory.get(
            '/admin/reconciliation/scheduledtask/',
            {'q': str(account.id)},
        )
        queryset = ScheduledTask.objects.all()

        results, _ = self.admin.get_search_results(
            request,
            queryset,
            str(account.id),
        )

        assert list(results.values_list('id', flat=True)) == [task.id]
