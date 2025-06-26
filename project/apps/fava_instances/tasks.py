# Beancount-Trans-Backend/project/apps/fava_instances/tasks.py
from celery import shared_task
from django.utils import timezone
from fava_instances.models import FavaInstance
from fava_instances.services.fava_manager import FavaContainerManager
from django.conf import settings

@shared_task
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
