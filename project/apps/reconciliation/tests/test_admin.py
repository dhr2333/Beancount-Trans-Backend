import pytest
from datetime import date

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory

from project.apps.account.models import Account
from project.apps.file_manager.models import Directory, File
from project.apps.reconciliation.admin import ScheduledTaskAdmin
from project.apps.reconciliation.models import ScheduledTask
from project.apps.translate.models import ParseFile


User = get_user_model()


@pytest.mark.django_db
class TestScheduledTaskAdminSearch:
    def setup_method(self):
        self.factory = RequestFactory()
        self.admin = ScheduledTaskAdmin(ScheduledTask, AdminSite())

    def test_search_by_username_includes_reconciliation_and_parse_review_tasks(self):
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
        parse_file_content_type = ContentType.objects.get_for_model(ParseFile)

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

        matched_directory = Directory.objects.create(name='Root', owner=matched_user)
        matched_file = File.objects.create(
            name='alice.csv',
            directory=matched_directory,
            storage_name='alice.csv',
            size=1,
            owner=matched_user,
            content_type='text/csv',
        )
        matched_parse_file = ParseFile.objects.create(
            file=matched_file,
            status='pending_review',
        )
        parse_review_task = ScheduledTask.objects.create(
            task_type='parse_review',
            content_type=parse_file_content_type,
            object_id=matched_parse_file.file_id,
            status='pending',
        )

        other_directory = Directory.objects.create(name='Root-Other', owner=other_user)
        other_file = File.objects.create(
            name='bob.csv',
            directory=other_directory,
            storage_name='bob.csv',
            size=1,
            owner=other_user,
            content_type='text/csv',
        )
        other_parse_file = ParseFile.objects.create(
            file=other_file,
            status='pending_review',
        )
        ScheduledTask.objects.create(
            task_type='parse_review',
            content_type=parse_file_content_type,
            object_id=other_parse_file.file_id,
            status='pending',
        )

        request = self.factory.get('/admin/reconciliation/scheduledtask/', {'q': 'alice'})
        queryset = ScheduledTask.objects.all()

        results, _ = self.admin.get_search_results(request, queryset, 'alice')

        assert set(results.values_list('id', flat=True)) == {
            reconciliation_task.id,
            parse_review_task.id,
        }

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
