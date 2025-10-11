from django.apps import AppConfig


class AccountConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'project.apps.account'
    label = 'account_config'

    def ready(self):
        """应用启动时导入信号处理器"""
        import project.apps.account.signals