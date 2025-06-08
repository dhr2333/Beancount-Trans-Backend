from django.db.models.signals import post_save
from django.dispatch import receiver
from file_manager.models import Directory
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_user_root_directory(sender, instance, created, **kwargs):
    if created:
        Directory.objects.create(
            name="Root",
            owner=instance,
            parent=None
        )
