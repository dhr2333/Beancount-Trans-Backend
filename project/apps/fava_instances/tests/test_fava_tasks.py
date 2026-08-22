"""
Fava 登录预热任务测试
"""
import pytest
from unittest.mock import patch, MagicMock
from django.db import transaction
from django.test import override_settings
from project.apps.fava_instances.tasks import schedule_fava_warmup, warmup_fava_container


@pytest.mark.django_db
class TestFavaWarmupTask:
    def test_schedule_enqueues_after_commit(self, user):
        with patch('project.apps.fava_instances.tasks.warmup_fava_container.delay') as mock_delay, \
             patch.object(transaction, 'on_commit', side_effect=lambda fn: fn()):
            schedule_fava_warmup(user)
        mock_delay.assert_called_once_with(user.pk)

    @override_settings(FAVA_DEPLOY_MODE='static')
    def test_schedule_skips_static_mode(self, user):
        with patch('project.apps.fava_instances.tasks.warmup_fava_container.delay') as mock_delay:
            schedule_fava_warmup(user)
        mock_delay.assert_not_called()

    def test_task_skips_in_testing(self, user):
        with patch('project.apps.fava_instances.tasks.FavaContainerManager') as mock_cls:
            assert warmup_fava_container(user.pk) == 'skipped_testing'
            mock_cls.assert_not_called()

    @override_settings(TESTING=False, FAVA_DEPLOY_MODE='dynamic')
    def test_task_starts_container(self, user):
        with patch('project.apps.fava_instances.tasks.FavaContainerManager') as mock_cls:
            mock_manager = MagicMock()
            mock_cls.return_value = mock_manager
            assert warmup_fava_container(user.pk) == 'ok'
            mock_manager.ensure_running.assert_called_once_with(user, touch_last_accessed=False)

    @override_settings(TESTING=False, FAVA_DEPLOY_MODE='static')
    def test_task_skips_static_mode(self, user):
        with patch('project.apps.fava_instances.tasks.FavaContainerManager') as mock_cls:
            assert warmup_fava_container(user.pk) == 'skipped_static'
            mock_cls.assert_not_called()

    @override_settings(TESTING=False)
    def test_task_missing_user(self):
        assert warmup_fava_container(999999) == 'user_not_found'

    @override_settings(TESTING=False, FAVA_DEPLOY_MODE='dynamic')
    def test_task_swallows_errors(self, user):
        with patch('project.apps.fava_instances.tasks.FavaContainerManager') as mock_cls:
            mock_cls.return_value.ensure_running.side_effect = Exception('boom')
            assert warmup_fava_container(user.pk) == 'error'
