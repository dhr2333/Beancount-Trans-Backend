# project/apps/translate/tasks.py
from celery import shared_task
from django.core.cache import cache
from project.apps.translate.models import ParseFile
# from project.apps.file_manager.models import File
from project.utils.storage_factory import get_storage_client
# from django.conf import settings
# from project.utils.file import BeanFileManager
from project.apps.translate.services.analyze_service import AnalyzeService
from project.apps.translate.services.parse_review_service import ParseReviewService
# from project.apps.translate.utils import get_user_config
from project.utils.tools import get_user_config
from project.apps.reconciliation.models import ScheduledTask
from django.contrib.contenttypes.models import ContentType
import logging
import time
# import json

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def parse_single_file_task(self, file_id, user_id, args):
    task_id = self.request.id

    try:
        # 获取ParseFile对象，检查是否已被取消
        parse_file = ParseFile.objects.get(file_id=file_id)
        if parse_file.status == 'cancelled':
            # 更新Redis状态
            cache.set(f'task_status:{task_id}', {
                'status': 'cancelled',
                'file_id': file_id,
                'error': None
            }, timeout=24*3600)
            return {'status': 'cancelled', 'file_id': file_id}

        # 更新Redis状态为processing
        cache.set(f'task_status:{task_id}', {
            'status': 'processing',
            'file_id': file_id,
            'error': None
        }, timeout=24*3600)

        # 更新状态为processing
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
        # args['write'] 的值由 MultiBillAnalyzeView 根据用户偏好设置

        service = AnalyzeService(user=user, config=config)
        result_context = service.analyze_single_file(uploaded_file, args)

        # 根据 write 标志决定处理方式
        should_write = args.get('write', True)
        
        if not should_write:
            # 审核模式：不写入文件，存入缓存，激活待办
            formatted_data = result_context.get('formatted_data', [])
            parsed_data = result_context.get('parsed_data', [])
            
            # 为每条记录补充 uuid 和 original_row
            # 从 parsed_data 中查找对应的记录
            parsed_data_dict = {entry.get('cache_key'): entry for entry in parsed_data}
            
            # 从 CacheStep 的缓存中获取 original_row
            enhanced_formatted_data = []
            for entry in formatted_data:
                cache_key = entry.get('id')  # FormatStep 输出的 id 就是 cache_key
                parsed_entry = parsed_data_dict.get(cache_key, {})
                
                # 从 CacheStep 的缓存中获取 original_row
                cache_entry_data = cache.get(cache_key)
                original_row = None
                if cache_entry_data and isinstance(cache_entry_data, dict):
                    original_row = cache_entry_data.get('original_row')
                
                enhanced_entry = {
                    'uuid': parsed_entry.get('uuid', cache_key),
                    'formatted': entry.get('formatted', ''),
                    'edited_formatted': entry.get('formatted', ''),  # 初始状态默认为 formatted
                    'selected_expense_key': entry.get('selected_expense_key', ''),
                    'expense_candidates_with_score': entry.get('expense_candidates_with_score', []),
                    'original_row': original_row
                }
                enhanced_formatted_data.append(enhanced_entry)
            
            # 准备缓存数据
            cache_data = {
                'file_id': file_id,
                'formatted_data': enhanced_formatted_data,
                'created_at': time.time(),
                'expires_at': time.time() + 86400  # 24小时后过期
            }
            
            # 保存到 Redis 缓存
            ParseReviewService.save_parse_result(file_id, cache_data)
            
            # 更新 ParseFile 状态为待审核
            parse_file.status = 'pending_review'
            parse_file.save()
            
            # 激活解析待办任务
            content_type = ContentType.objects.get_for_model(ParseFile)
            parse_review_task = ScheduledTask.objects.filter(
                task_type='parse_review',
                content_type=content_type,
                object_id=file_id,
                status='inactive'
            ).first()
            
            if parse_review_task:
                parse_review_task.status = 'pending'
                parse_review_task.save()
            
            # 更新 Redis 状态为 pending_review
            cache.set(f'task_status:{task_id}', {
                'status': 'pending_review',
                'file_id': file_id,
                'error': None
            }, timeout=24*3600)
            
            return {
                'status': 'pending_review',
                'file_id': file_id
            }
        else:
            # 直接写入模式：保持原有逻辑
            # 更新状态
            parse_file.status = 'parsed'
            parse_file.save()

            # 更新状态为parsed
            cache.set(f'task_status:{task_id}', {
                'status': 'parsed',
                'file_id': file_id,
                'error': None
            }, timeout=24*3600)

            return {
                'status': 'parsed',
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


@shared_task
def auto_confirm_expired_parse_reviews():
    """定时任务：到期自动确认写入
    
    每小时执行一次，扫描所有过期的解析待办（创建时间超过24小时），
    自动确认写入，更新状态为已完成
    """
    from datetime import timedelta
    from django.utils import timezone
    from project.apps.reconciliation.models import ScheduledTask
    from django.contrib.contenttypes.models import ContentType
    from project.apps.translate.services.parse_review_service import ParseReviewService
    from project.apps.translate.utils.beancount_validator import BeancountValidator
    from project.utils.file import BeanFileManager
    
    logger.info("开始执行到期自动确认写入任务")
    
    # 获取所有待审核的解析待办
    content_type = ContentType.objects.get_for_model(ParseFile)
    pending_tasks = ScheduledTask.objects.filter(
        task_type='parse_review',
        status='pending',
        content_type=content_type
    )
    
    # 计算24小时前的时间（使用 timezone-aware datetime）
    expire_time = timezone.now() - timedelta(hours=24)
    
    confirmed_count = 0
    error_count = 0
    
    for task in pending_tasks:
        # 检查创建时间是否超过24小时
        if task.created < expire_time:
            try:
                parse_file = task.content_object
                
                # 从缓存获取最终结果
                final_entries = ParseReviewService.get_final_result(parse_file.file_id)
                
                if not final_entries:
                    logger.warning(f"解析结果不存在或已过期: file_id={parse_file.file_id}")
                    # 如果缓存已过期，直接标记为已完成（避免重复处理）
                    task.status = 'completed'
                    task.save()
                    parse_file.status = 'parsed'
                    parse_file.save()
                    confirmed_count += 1
                    continue
                
                # 合并所有条目
                formatted_text = '\n\n'.join([
                    entry['formatted'].rstrip() for entry in final_entries
                ])
                
                # 进行 Beancount 语法校验
                is_valid, error_message, _ = BeancountValidator.validate_entries(formatted_text)
                
                if not is_valid:
                    logger.error(f"Beancount 语法错误，跳过自动确认: file_id={parse_file.file_id}, error={error_message}")
                    error_count += 1
                    continue
                
                # 写入文件
                user = parse_file.file.owner
                original_filename = parse_file.file.name
                bean_file_path = BeanFileManager.get_bean_file_path(user, original_filename)
                
                with open(bean_file_path, 'w', encoding='utf-8') as f:
                    f.write(formatted_text)
                
                # 更新状态
                parse_file.status = 'parsed'
                parse_file.save()
                
                task.status = 'completed'
                task.save()
                
                confirmed_count += 1
                logger.info(f"自动确认写入成功: file_id={parse_file.file_id}, task_id={task.id}")
                
            except Exception as e:
                logger.error(f"自动确认写入失败: task_id={task.id}, error={str(e)}", exc_info=True)
                error_count += 1
                continue
    
    logger.info(f"到期自动确认写入任务完成: 成功={confirmed_count}, 失败={error_count}")
    return {
        'confirmed_count': confirmed_count,
        'error_count': error_count
    }