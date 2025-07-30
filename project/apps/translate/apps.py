from django.apps import AppConfig


class TranslateConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'project.apps.translate'

    def ready(self):
        # 注册信号
        import project.apps.translate.signals