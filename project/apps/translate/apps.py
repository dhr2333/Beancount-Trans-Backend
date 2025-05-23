from django.apps import AppConfig


class TranslateConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'translate'

    def ready(self):
        # 注册信号
        import translate.signals