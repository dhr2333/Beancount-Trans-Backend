# project/apps/file_manager/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from project.apps.file_manager.models import Directory, File
from project.apps.translate.models import ParseFile
from project.utils.file import BeanFileManager
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_user_root_directory(sender, instance, created, **kwargs):
    if created:
        Directory.objects.create(
            name="Root",
            owner=instance,
            parent=None
        )

@receiver(post_save, sender=User)
def create_sample_files_for_new_user(sender, instance, created, **kwargs):
    """为新用户创建案例文件引用"""
    if created:
        # 获取 admin 用户的案例文件
        try:
            admin_user = User.objects.get(id=1)
        except User.DoesNotExist:
            # 如果没有 admin 用户，跳过
            return

        # 查找 admin 用户的 Root 目录
        admin_root_dir = Directory.objects.filter(
            name='Root',
            owner=admin_user,
            parent__isnull=True
        ).first()

        if not admin_root_dir:
            # 如果没有 Root 目录，跳过
            return

        # 获取 admin 用户的案例文件
        admin_files = File.objects.filter(
            owner=admin_user,
            directory=admin_root_dir,
            name__in=['完整测试_微信.csv', '完整测试_支付宝.csv']
        )

        if not admin_files.exists():
            # 如果没有案例文件，跳过
            return

        # 获取新用户的 Root 目录
        new_root_dir = Directory.objects.filter(
            name='Root',
            owner=instance,
            parent__isnull=True
        ).first()

        if not new_root_dir:
            # 如果没有 Root 目录，跳过
            return

        # 为新用户创建文件引用
        for admin_file in admin_files:
            # 创建文件引用（使用相同的 storage_name）
            new_file = File.objects.create(
                name=admin_file.name,
                directory=new_root_dir,  # 使用新用户的 Root 目录
                storage_name=admin_file.storage_name,  # 关键：使用相同的存储名称
                size=admin_file.size,
                owner=instance,
                content_type=admin_file.content_type
            )

            # 创建解析记录
            ParseFile.objects.create(file=new_file)

            # 创建对应的 .bean 文件
            bean_filename = BeanFileManager.create_bean_file(
                instance,
                admin_file.name
            )
            BeanFileManager.update_main_bean_include(
                instance,
                bean_filename,
                action='add'
            )
