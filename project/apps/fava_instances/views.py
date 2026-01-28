# Beancount-Trans-Backend/project/apps/fava_instances/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from project.apps.fava_instances.models import FavaInstance
from project.apps.fava_instances.services.fava_manager import FavaContainerManager
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
import os
from django.conf import settings
import logging


logger = logging.getLogger(__name__)

class FavaRedirectView(APIView):
    """
    触发启动fava容器并重定向

    该视图的URL可能是`/api/fava/`（不带uuid）
    它检查当前用户的`FavaInstance`，如果不存在或者状态不是运行中，则启动一个新的容器（同步启动，等待容器启动完成，然后更新`FavaInstance`的状态为`running`）
    然后可以直接访问fava容器的页面
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        logger.info(f"User {user.username} is requesting Fava instance.")
        manager = FavaContainerManager()
        
        # 检查现有运行实例
        running_instance = FavaInstance.objects.filter(
            owner=user,
            status='running'
        ).first()

        if running_instance:
            # 验证容器是否真实存在
            if manager.verify_and_cleanup_instance(running_instance):
                # 容器存在，直接返回重定向
                running_instance.save()
                logger.info(f"用户 {user.username} 的实例 {running_instance.uuid} 容器运行正常，返回重定向")
                return Response(
                    status=status.HTTP_302_FOUND,
                    headers={'Location': f'/{running_instance.uuid}/'}
                )
            else:
                # 容器不存在，已清理数据库记录，继续创建新实例
                logger.info(f"用户 {user.username} 的实例 {running_instance.uuid} 容器不存在，已清理数据库记录")

        # 清理用户的所有旧实例（包括 starting、error 等状态）
        logger.info(f"清理用户 {user.username} 的所有旧实例")
        manager.cleanup_user_containers(user)

        # 创建新实例
        instance = FavaInstance(owner=user, status='starting')
        instance.save()
        logger.info(f"为用户 {user.username} 创建新实例 {instance.uuid}")

        # 准备bean文件路径
        from project.utils.file import BeanFileManager
        user_assets_path = BeanFileManager.get_user_assets_path(user)
        bean_file = os.path.join(settings.ASSETS_HOST_PATH, os.path.basename(user_assets_path))

        # 启动容器
        try:
            container_id, container_name = manager.start_container(user, bean_file, instance)

            instance.container_id = container_id
            instance.container_name = container_name
            instance.status = 'running'
            instance.save()
            logger.info(f"用户 {user.username} 的实例 {instance.uuid} 容器启动成功")

            return Response(
                status=status.HTTP_302_FOUND,
                headers={'Location': f'/{instance.uuid}/'}
            )

        except Exception as e:
            logger.error(f"用户 {user.username} 的实例 {instance.uuid} 容器启动失败: {str(e)}")
            # 启动失败，清理新实例记录
            try:
                instance.container_id = ''
                instance.container_name = ''
                instance.status = 'error'
                instance.save()
                logger.info(f"已清理启动失败的实例 {instance.uuid} 的记录")
            except Exception as cleanup_error:
                logger.error(f"清理失败实例 {instance.uuid} 时出错: {str(cleanup_error)}")
            
            return Response(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                data={'error': str(e)}
            )


class FavaStopView(APIView):
    """
    停止用户的Fava实例

    该视图用于在用户退出登录时停止其Fava容器实例
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        logger.info(f"User {user.username} is requesting to stop Fava instance.")

        # 查找用户的所有运行中的Fava实例
        running_instances = FavaInstance.objects.filter(
            owner=user,
            status__in=['running', 'starting']
        )

        if not running_instances.exists():
            return Response(
                status=status.HTTP_200_OK,
                data={'message': 'No running Fava instances found for this user.'}
            )

        manager = FavaContainerManager()
        stopped_count = 0

        for instance in running_instances:
            try:
                # 更新实例状态为停止中
                instance.status = 'stopping'
                instance.save()

                # 停止容器
                if manager.stop_container(instance.container_id):
                    instance.status = 'stopped'
                    instance.container_id = ''
                    instance.container_name = ''
                    stopped_count += 1
                else:
                    instance.status = 'error'

                instance.save()

            except Exception as e:
                logger.error(f"Error stopping Fava instance {instance.uuid}: {str(e)}")
                instance.status = 'error'
                instance.save()

        return Response(
            status=status.HTTP_200_OK,
            data={
                'message': f'Successfully stopped {stopped_count} Fava instance(s).',
                'stopped_count': stopped_count
            }
        )
