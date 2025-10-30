from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'project.apps.authentication'
    verbose_name = '用户认证'

    def ready(self):
        import project.apps.authentication.signals  # noqa

