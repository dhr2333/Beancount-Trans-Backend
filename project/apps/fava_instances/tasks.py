# Beancount-Trans-Backend/project/apps/fava_instances/tasks.py
import logging
from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from project.apps.fava_instances.models import FavaInstance
from project.apps.fava_instances.services.fava_manager import FavaContainerManager

logger = logging.getLogger(__name__)


def schedule_fava_warmup(user):
    """
    登录成功后异步预热 Fava 容器，不阻塞签发 JWT。

    生命周期仍按 last_accessed + FAVA_CONTAINER_LIFETIME 回收，
    JWT 续期或页面刷新不会再次预热，也不会让容器一直活着。
    """
    if getattr(settings, 'FAVA_DEPLOY_MODE', 'dynamic') == 'static':
        return
    user_id = user.pk

    def _enqueue():
        try:
            warmup_fava_container.delay(user_id)
        except Exception:
            logger.exception("调度 Fava 预热失败: user_id=%s", user_id)

    transaction.on_commit(_enqueue)


@shared_task(name="fava_instances.tasks.warmup_fava_container")
def warmup_fava_container(user_id):
    if getattr(settings, 'FAVA_DEPLOY_MODE', 'dynamic') == 'static':
        return 'skipped_static'
    # 登录测试走 CELERY_TASK_ALWAYS_EAGER，避免连上本机 Docker 真起容器
    if getattr(settings, 'TESTING', False):
        return 'skipped_testing'

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("Fava 预热跳过：用户不存在 user_id=%s", user_id)
        return 'user_not_found'

    try:
        FavaContainerManager().ensure_running(user, touch_last_accessed=False)
        return 'ok'
    except Exception:
        logger.exception("Fava 预热失败: user_id=%s", user_id)
        return 'error'


@shared_task(name="fava_instances.tasks.cleanup_fava_containers")
def cleanup_fava_containers():
    expiry = timezone.now() - settings.FAVA_CONTAINER_LIFETIME
    instances = FavaInstance.objects.filter(
        last_accessed__lt=expiry,
        status__in=['running', 'starting']
    )

    manager = FavaContainerManager()
    for instance in instances:
        instance.status = 'stopping'
        instance.save()

        if manager.stop_container(instance.container_id):
            instance.status = 'stopped'
            instance.container_id = ''
            instance.container_name = ''
        else:
            instance.status = 'error'

        instance.save()
