from django.apps import AppConfig


class FavaInstancesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'project.apps.fava_instances'

    def ready(self):
        from project.apps.fava_instances import tasks
