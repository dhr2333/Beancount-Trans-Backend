# project/apps/translate/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from project.apps.translate.models import FormatConfig

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_config(sender, instance, created, **kwargs):
    """用户创建时自动生成默认配置"""
    if created:
        FormatConfig.get_user_config(user=instance)