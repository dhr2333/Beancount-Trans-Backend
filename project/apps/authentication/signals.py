import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from project.apps.authentication.models import UserProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """当创建新用户时，自动创建对应的 UserProfile"""
    if created:
        try:
            UserProfile.objects.create(user=instance)
            logger.info(f"为用户 {instance.username} 创建了 UserProfile")
        except Exception as e:
            logger.error(f"创建 UserProfile 失败: {str(e)}")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """保存用户时，确保 UserProfile 存在"""
    try:
        if hasattr(instance, 'profile'):
            instance.profile.save()
        else:
            UserProfile.objects.create(user=instance)
            logger.info(f"为用户 {instance.username} 补充创建了 UserProfile")
    except Exception as e:
        logger.error(f"保存 UserProfile 失败: {str(e)}")

