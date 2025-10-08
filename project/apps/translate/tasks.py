# project/apps/translate/tasks.py
from celery import shared_task
from django.core.cache import cache
from project.apps.translate.models import ParseFile
# from project.apps.file_manager.models import File
from project.utils.storage_factory import get_storage_client
# from django.conf import settings
# from project.utils.file import BeanFileManager
from project.apps.translate.services.analyze_service import AnalyzeService
# from project.apps.translate.utils import get_user_config
from project.utils.tools import get_user_config
import logging
# import json

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def parse_single_file_task(self, file_id, user_id, args):
    task_id = self.request.id

    try:
        # 更新Redis状态为processing
        cache.set(f'task_status:{task_id}', {
            'status': 'processing',
            'file_id': file_id,
            'error': None
        }, timeout=24*3600)

        # 获取ParseFile对象
        parse_file = ParseFile.objects.get(file_id=file_id)
        parse_file.status = 'processing'
        parse_file.save()

        # {"group_id": "988da899-5ec0-4af1-8568-db81afa6bbbf", "created_at": 1754963160.402835, "file_ids": [26, 27], "task_ids": [null, null], "status": "processing"}
        # 获取文件对象

        file_obj = parse_file.file
        storage_client = get_storage_client()

        # 从存储获取文件内容
        file_data = storage_client.download_file(file_obj.storage_name)
        if file_data is None:
            raise Exception(f"文件不存在: {file_obj.storage_name}")

        file_content = file_data.read()

        # 创建模拟文件对象
        from io import BytesIO
        from django.core.files.uploadedfile import InMemoryUploadedFile
        file_stream = BytesIO(file_content)
        uploaded_file = InMemoryUploadedFile(
            file_stream,
            None,  # field_name
            file_obj.name,
            file_obj.content_type,
            len(file_content),
            None  # charset
        )

        # 解析文件
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=user_id)
        config = get_user_config(user)
        args['write'] = True  # 多文件解析默认写入文件

        service = AnalyzeService(user=user, config=config)
        service.analyze_single_file(uploaded_file, args)

        # 更新状态
        parse_file.status = 'success'
        parse_file.save()

        # 更新状态为success
        cache.set(f'task_status:{task_id}', {
            'status': 'success',
            'file_id': file_id,
            'error': None
        }, timeout=24*3600)

        return {
            'status': 'success',
            'file_id': file_id
        }

    except Exception as e:
        logger.error(f"文件解析失败: {file_id}, 错误: {str(e)}")
        parse_file = ParseFile.objects.get(file_id=file_id)
        parse_file.status = 'failed'
        parse_file.error_message = str(e)
        parse_file.save()

        return {
            'status': 'failed',
            'file_id': file_id,
            'error': str(e)
        }