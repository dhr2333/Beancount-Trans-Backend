from django.apps import AppConfig


class FileManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'project.apps.file_manager'

    def ready(self):
        import project.apps.file_manager.signals