# Beancount-Trans-Backend/project/apps/fava_instances/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from project.apps.fava_instances.models import FavaInstance
from project.apps.fava_instances.services.fava_manager import FavaContainerManager
from project.utils.fava_static import resolve_static_fava_url
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
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

        if settings.FAVA_DEPLOY_MODE == 'static':
            url = resolve_static_fava_url(user, settings.FAVA_STATIC_USER_MAP)
            if not url:
                return Response(
                    {
                        'error': '未配置静态 Fava 入口：请在环境变量 FAVA_STATIC_USER_MAP 中为该用户或账本目录名设置可访问的 URL',
                        'code': 'FAVA_STATIC_NOT_CONFIGURED',
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(
                status=status.HTTP_200_OK,
                data={'url': url, 'deploy_mode': 'static'},
            )

        try:
            instance = FavaContainerManager().ensure_running(user, touch_last_accessed=True)
            return Response(
                status=status.HTTP_302_FOUND,
                headers={'Location': f'/{instance.uuid}/'}
            )
        except Exception as e:
            logger.error(f"用户 {user.username} 启动 Fava 容器失败: {str(e)}")
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

        if settings.FAVA_DEPLOY_MODE == 'static':
            return Response(
                status=status.HTTP_200_OK,
                data={'message': '静态 Fava 模式无需停止实例', 'stopped_count': 0},
            )

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
