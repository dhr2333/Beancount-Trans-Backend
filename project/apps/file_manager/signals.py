# project/apps/file_manager/signals.py
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from project.apps.file_manager.models import Directory, File
from project.apps.translate.models import ParseFile
from project.utils.file import BeanFileManager
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_root_directory(sender, instance, created, **kwargs):
    """为新用户创建 Root 目录（数据库记录）"""
    if created:
        Directory.objects.create(
            name="Root",
            owner=instance,
            parent=None
        )
        logger.debug(f"为用户 {instance.username} 创建了 Root 目录")


@receiver(post_save, sender=User)
def init_user_bean_structure_on_create(sender, instance, created, **kwargs):
    """用户创建时初始化完整的账本文件结构"""
    if created:
        try:
            BeanFileManager.init_user_bean_structure(instance)
            logger.info(f"为用户 {instance.username} 初始化账本文件结构成功")
        except Exception as e:
            logger.error(f"为用户 {instance.username} 初始化账本文件结构失败: {str(e)}")
            # 不阻断用户创建流程，只记录错误


@receiver(post_save, sender=User)
def create_sample_files_for_new_user(sender, instance, created, **kwargs):
    """为新用户创建案例文件引用"""
    if created:
        # 获取 admin 用户的案例文件
        try:
            admin_user = User.objects.get(id=1)
        except User.DoesNotExist:
            # 如果没有 admin 用户，跳过
            logger.debug("没有 admin 用户，跳过创建示例文件")
            return

        # 查找 admin 用户的 Root 目录
        admin_root_dir = Directory.objects.filter(
            name='Root',
            owner=admin_user,
            parent__isnull=True
        ).first()

        if not admin_root_dir:
            # 如果没有 Root 目录，跳过
            logger.debug("admin 用户没有 Root 目录，跳过创建示例文件")
            return

        # 获取 admin 用户的案例文件
        admin_files = File.objects.filter(
            owner=admin_user,
            directory=admin_root_dir,
            name__in=['完整测试_微信.csv', '完整测试_支付宝.csv']
        )

        if not admin_files.exists():
            # 如果没有案例文件，跳过
            logger.debug("admin 用户没有案例文件，跳过创建示例文件")
            return

        # 获取新用户的 Root 目录
        new_root_dir = Directory.objects.filter(
            name='Root',
            owner=instance,
            parent__isnull=True
        ).first()

        if not new_root_dir:
            # 如果没有 Root 目录，跳过
            logger.warning(f"用户 {instance.username} 没有 Root 目录，跳过创建示例文件")
            return

        # 为新用户创建文件引用
        for admin_file in admin_files:
            try:
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
                
                # 向 trans/main.bean 添加对应文件的 include
                BeanFileManager.add_bean_to_trans_main(
                    instance,
                    bean_filename
                )
                
                logger.debug(f"为用户 {instance.username} 创建示例文件: {admin_file.name}")
            except Exception as e:
                logger.error(f"为用户 {instance.username} 创建示例文件 {admin_file.name} 失败: {str(e)}")
                # 继续处理其他文件
