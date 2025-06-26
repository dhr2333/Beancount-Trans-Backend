# Beancount-Trans-Backend/project/apps/fava_instances/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from fava_instances.models import FavaInstance
from fava_instances.services.fava_manager import FavaContainerManager
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
        # 检查现有运行实例
        running_instance = FavaInstance.objects.filter(
            owner=user,
            status='running'
        ).first()
        
        if running_instance:
            running_instance.save()
            return Response(
                status=status.HTTP_302_FOUND,
                headers={'Location': f'/{running_instance.uuid}/'}
            )

        # 创建新实例
        instance = FavaInstance(owner=user, status='starting')
        instance.save()

        # 准备bean文件路径
        bean_file = os.path.join(settings.BEANCOUNT_ROOT,user.username,'main.bean')

        logger.info(f"bean_file path: {bean_file}","启动容器")
        # 启动容器
        try:
            manager = FavaContainerManager()
            container_id, container_name = manager.start_container(user, bean_file, instance)

            instance.container_id = container_id
            instance.container_name = container_name
            instance.status = 'running'
            instance.save()
            
            return Response(
                status=status.HTTP_302_FOUND,
                headers={'Location': f'/{instance.uuid}/'}
            )

        except Exception as e:
            instance.status = 'error'
            instance.save()
            return Response(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                data={'error': str(e)}
            )
