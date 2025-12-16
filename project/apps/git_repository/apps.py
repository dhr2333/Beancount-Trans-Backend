from django.apps import AppConfig


class GitRepositoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'project.apps.git_repository'
    verbose_name = 'Git 仓库管理'
