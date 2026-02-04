# project/apps/translate/views/views.py
import logging
import uuid
import json
import time
import os
from celery.result import GroupResult
from celery import group
from django.core.cache import cache
from django.shortcuts import render
from django.contrib.auth import get_user_model
from project.utils.exceptions import UnsupportedFileTypeError, DecryptionError
from project.utils.token import get_token_user_id
from project.utils.tools import get_user_config
from project.apps.common.permissions import IsOwnerOrAdminReadWriteOnly, AnonymousReadOnlyPermission
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from project.apps.translate.models import FormatConfig, ParseFile
from project.apps.translate.serializers import AnalyzeSerializer, FormatConfigSerializer, ReparseSerializer
from project.apps.translate.utils import FormatData
from project.apps.translate.tasks import parse_single_file_task
from project.apps.translate.services.analyze_service import AnalyzeService
from project.apps.translate.services.parse.transaction_parser import single_parse_transaction
from project.apps.reconciliation.models import ScheduledTask
from django.contrib.contenttypes.models import ContentType
from project.apps.translate.utils import FormatData



User = get_user_model()
logger = logging.getLogger(__name__)


class BillAnalyzeView(APIView):
    """单账单解析接口

    Args:
        APIView (_type_): _description_

    Returns:
        _type_: _description_
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AnalyzeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        owner_id = get_token_user_id(request)
        config = get_user_config(User.objects.get(id=owner_id))

        uploaded_file = request.FILES.get('trans', None)
        if not uploaded_file:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        service = AnalyzeService(owner_id, config)
        try:
            result = service.analyze(uploaded_file, serializer.validated_data)
            return Response(result, status=status.HTTP_200_OK)
        except DecryptionError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except UnsupportedFileTypeError as e:
            return Response({'error': str(e)}, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(e)
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        return render(request, "translate/trans.html", {"title": "trans"})


class UserConfigAPI(APIView):
    """用户个人配置接口
    
    支持匿名用户获取格式化输出配置（只读），匿名用户将获取 id=1 用户的配置。
    只有认证用户可以更新配置。
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [AnonymousReadOnlyPermission]

    def get(self, request):
        """获取当前用户配置（匿名用户获取 id=1 用户的配置）"""
        config = FormatConfig.get_user_config(request.user)
        serializer = FormatConfigSerializer(config)
        return Response(serializer.data)

    def put(self, request):
        """更新当前用户配置（需要认证）"""
        if not request.user.is_authenticated:
            return Response(
                {'error': '需要登录才能更新配置'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        config = FormatConfig.get_user_config(request.user)
        serializer = FormatConfigSerializer(
            config,
            data=request.data,
            partial=True  # 允许部分更新
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response({
            "status": "error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class SingleBillAnalyzeView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AnalyzeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取用户ID和配置
        # owner_id = get_token_user_id(request)
        user = User.objects.get(id=get_token_user_id(request))
        config = get_user_config(User.objects.get(id=get_token_user_id(request)))

        # 获取上传文件
        uploaded_file = request.FILES.get('trans', None)
        if not uploaded_file:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        # 创建服务并解析
        service = AnalyzeService(user=user, config=config)
        results = []
        try:
            context = service.analyze_single_file(uploaded_file, serializer.validated_data)
            formatted_data_list = context["formatted_data"]
            for formatted_data in formatted_data_list:
                if isinstance(formatted_data, dict):
                    results.append({
                        # "id": formatted_data.get("uuid") or formatted_data.get("id"),
                        "id": formatted_data.get("id"),
                        "formatted": formatted_data.get("formatted"),
                        "ai_choose": formatted_data.get("selected_expense_key"),
                        "ai_candidates": formatted_data.get("expense_candidates_with_score", []),
                    })
                else:
                    results.append({
                        # "id": formatted_data.get("uuid") or formatted_data.get("id"),
                        "id": formatted_data.get("id"),
                        "formatted": formatted_data,
                        "ai_choose": None,
                        "ai_candidates": [],
                    })
            response_data = {
            "results": results,
            "summary": {"count": len(results)},
            "status": "success"
            }
            return Response(response_data, status=status.HTTP_200_OK)
        # except DecryptionError as e:
        #     return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        # except UnsupportedFileTypeError as e:
        #     return Response({'error': str(e)}, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        # except ValueError as e:
        #     return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(e)
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReparseEntryView(APIView):
    """AI反馈重新解析接口

    此视图处理AI反馈条目的重新解析请求，对指定条目执行新的分析并返回更新后的解析结果。

    Args:
        entry_id (str): 要重新解析的条目ID
        user_selected_key (str): 用户选择的映射关键字

    Returns:
        entry_id (str): 要重新解析的条目ID
        formatted (str): 解析后的条目内容
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ReparseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entry_id = serializer.validated_data['entry_id']
        selected_key = serializer.validated_data['selected_key']
        cache_key = entry_id
        cache_data = cache.get(cache_key)

        if not cache_data:
            return Response({'error': '缓存已过期或记录不存在'}, status=status.HTTP_404_NOT_FOUND)

        original_row = cache_data['original_row']
        owner_id = get_token_user_id(request)
        config = get_user_config(User.objects.get(id=owner_id))
        # 重新解析交易记录
        try:
            parsed_entry = single_parse_transaction(original_row, owner_id, config, selected_key)

            formatted = FormatData.format_instance(parsed_entry, config=config)

            # 更新缓存
            cache.set(cache_key, {
                "parsed_entry": parsed_entry,
                "original_row": original_row,
            }, timeout=3600)
            return Response({
                "id": entry_id,
                "formatted": formatted,
                "ai_choose": selected_key,
                "ai_candidates": parsed_entry['expense_candidates_with_score']
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(e)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MultiBillAnalyzeView(APIView):
    """多账单解析接口

    该接口实现解析单个/多个文件

    Args:
        files (list): 上传的文件列表

    Returns:
        包含Celery任务组 ID 的响应
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_ids = request.data.get('file_ids', [])

        # 检查文件是否已在处理中
        pending_files = []
        for file_id in file_ids:
            parse_file = ParseFile.objects.filter(file_id=file_id).first()
            if parse_file and parse_file.status in ['pending', 'processing']:
                pending_files.append(file_id)

        if pending_files:
            return Response({
                'error': '部分文件已在处理队列中',
                'pending_files': pending_files
            }, status=status.HTTP_400_BAD_REQUEST)

        # 获取用户的解析模式偏好
        config = FormatConfig.get_user_config(request.user)
        parsing_mode = config.parsing_mode_preference if hasattr(config, 'parsing_mode_preference') else 'review'
        
        # 更新文件状态为待处理
        for file_id in file_ids:
            parse_file, _ = ParseFile.objects.get_or_create(file_id=file_id)
            parse_file.status = 'pending'
            parse_file.save()

        # 创建任务组
        tasks = []
        # 根据用户偏好设置是否立即写入
        # 审核模式：不立即写入，生成解析待办
        # 直接写入模式：立即写入文件
        args = {
            'write': (parsing_mode == 'direct_write'),
            'cmb_credit_ignore': True,
            'boc_debit_ignore': True,
            'password': None,
            'balance': False,
            'isCSVOnly': False
            # 'ignore_level': request.data.get('ignore_level', 'basic')  # 忽略级别
        }

        for file_id in file_ids:
            task = parse_single_file_task.s(file_id, request.user.id, args)
            tasks.append(task)

        task_group = group(tasks)
        group_result = task_group.apply_async()

         # 获取每个任务的任务ID
        task_ids = [task.id for task in group_result.children] if group_result.children else []

        # 生成任务组ID（使用UUID避免冲突）
        task_group_id = str(uuid.uuid4())

        # 存储任务组信息到Redis
        task_group_info = {
            'group_id': group_result.id,
            'created_at': time.time(),
            'file_ids': file_ids,
            'task_ids': task_ids,
            'status': 'pending'
        }
        cache.set(f'task_group:{task_group_id}', json.dumps(task_group_info), timeout=24*3600)

        # 初始化任务状态
        for task_id in task_group_info['task_ids']:
            cache.set(f'task_status:{task_id}', {
                'status': 'pending',
                'file_id': file_ids[task_group_info['task_ids'].index(task_id)]
            }, timeout=24*3600)

        # 如果是审核模式，返回解析待办ID列表
        response_data = {
            'task_group_id': task_group_id,
            'status': 'pending'
        }
        
        if parsing_mode == 'review':
            # 获取解析待办ID列表
            content_type = ContentType.objects.get_for_model(ParseFile)
            parse_review_tasks = ScheduledTask.objects.filter(
                task_type='parse_review',
                content_type=content_type,
                object_id__in=file_ids,
                status='inactive'
            )
            parse_review_task_ids = list(parse_review_tasks.values_list('id', flat=True))
            response_data['parse_review_task_ids'] = parse_review_task_ids

        return Response(response_data, status=status.HTTP_202_ACCEPTED)


class TaskGroupStatusView(APIView):
    """任务组状态查询接口
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        task_group_id = request.query_params.get('task_group_id')
        # task_group_id = request.data.get('task_group_id')
        if not task_group_id:
            return Response({'error': '缺少任务组ID'}, status=status.HTTP_400_BAD_REQUEST)

        # 从缓存获取任务组信息
        task_group_info = cache.get(f'task_group:{task_group_id}')
        if not task_group_info:
            return Response({'error': '任务组不存在或已过期'}, status=status.HTTP_404_NOT_FOUND)

        task_group_info = json.loads(task_group_info)
        group_result = GroupResult.restore(task_group_info['group_id'])

        # 获取所有任务状态
        tasks_status = []
        completed_count = 0

        for task_id in task_group_info['task_ids']:
            task_status = cache.get(f'task_status:{task_id}') or {'status': 'unknown'}
            tasks_status.append({
                'task_id': task_id,
                'file_id': task_status.get('file_id'),
                'status': task_status['status'],
                'error': task_status.get('error')
            })
            # pending_review 表示解析已完成，只是需要审核，应该计入已完成
            if task_status['status'] in ['parsed', 'failed', 'cancelled', 'pending_review']:
                completed_count += 1

        # 检查整体状态
        if completed_count == len(tasks_status):
            # 所有子任务都已完成（无论成功/失败）
            task_group_info['status'] = 'completed'
        elif group_result and group_result.ready():
            task_group_info['status'] = 'completed'
        else:
            task_group_info['status'] = 'processing'

        # 更新缓存
        cache.set(f'task_group:{task_group_id}', json.dumps(task_group_info), timeout=24*3600)

        return Response({
            'task_group_id': task_group_id,
            'status': task_group_info['status'],
            'progress': f'{completed_count}/{len(tasks_status)}',
            'tasks': tasks_status
        })


class CancelParseView(APIView):
    """取消解析接口

    取消指定文件的解析任务
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_ids = request.data.get('file_ids', [])
        if not file_ids:
            return Response({'error': '缺少文件ID列表'}, status=status.HTTP_400_BAD_REQUEST)

        from project.apps.file_manager.models import File
        from project.utils.file import BeanFileManager

        cancelled_files = []
        for file_id in file_ids:
            try:
                # 验证文件是否属于当前用户
                file_obj = File.objects.get(id=file_id, owner=request.user)
                
                # 获取或创建 ParseFile 对象
                parse_file, _ = ParseFile.objects.get_or_create(file_id=file_id)
                
                # 检查状态是否可以取消（pending/processing/parsed都可以取消）
                # parsed 状态取消时清除 .bean 文件内容
                if parse_file.status not in ['pending', 'processing', 'parsed']:
                    continue  # 跳过不能取消的状态
                
                # 更新状态为 cancelled
                parse_file.status = 'cancelled'
                parse_file.save()
                
                # 清空对应的 .bean 文件内容
                base_name = os.path.splitext(file_obj.name)[0]
                bean_filename = f"{base_name}.bean"
                BeanFileManager.clear_bean_file(request.user, bean_filename)
                
                # 更新对应的解析待办任务状态为 inactive（如果存在）
                # 这样用户可以重新解析文件
                content_type = ContentType.objects.get_for_model(ParseFile)
                parse_review_task = ScheduledTask.objects.filter(
                    task_type='parse_review',
                    content_type=content_type,
                    object_id=file_id
                ).first()
                
                if parse_review_task:
                    # 如果任务已完成，重置为 inactive 以便重新解析
                    if parse_review_task.status == 'completed':
                        parse_review_task.status = 'inactive'
                        parse_review_task.save()
                    # 如果任务处于 pending 状态，也重置为 inactive
                    elif parse_review_task.status == 'pending':
                        parse_review_task.status = 'inactive'
                        parse_review_task.save()
                
                cancelled_files.append(file_id)
                
                # 注意：这里无法直接撤销已提交到 Celery 队列的任务
                # 任务执行时会检查 ParseFile.status，如果已经是 cancelled 会直接返回
                # 这样可以实现软取消：标记状态为 cancelled，任务开始执行时发现已取消就不处理
                        
            except File.DoesNotExist:
                logger.warning(f"文件不存在或不属于当前用户: file_id={file_id}, user={request.user.username}")
                continue
            except Exception as e:
                logger.error(f"取消解析失败: file_id={file_id}, error={str(e)}")
                continue

        if not cancelled_files:
            return Response({'error': '没有可取消的文件'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': f'成功处理 {len(cancelled_files)} 个文件（已取消解析并清除解析结果）',
            'cancelled_files': cancelled_files
        }, status=status.HTTP_200_OK)


class ParseReviewViewSet(APIView):
    """解析待办审核视图集
    
    提供解析待办的审核功能，包括获取结果、重解析、编辑、确认写入等
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_task_and_file(self, request, task_id):
        """获取待办任务和关联的文件"""
        try:
            task = ScheduledTask.objects.get(id=task_id, task_type='parse_review')
            
            # 验证权限：确保待办关联的文件属于当前用户
            parse_file = task.content_object
            
            if parse_file is None:
                return None, None, Response(
                    {'error': '待办任务关联的文件不存在'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if parse_file.file.owner != request.user:
                return None, None, Response(
                    {'error': '无权访问此待办任务'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return task, parse_file, None
        except ScheduledTask.DoesNotExist:
            return None, None, Response(
                {'error': '待办任务不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"获取待办任务失败: {str(e)}", exc_info=True)
            return None, None, Response(
                {'error': f'获取待办任务失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ParseReviewResultsView(ParseReviewViewSet):
    """获取解析结果"""
    
    def get(self, request, task_id):
        """获取解析结果
        
        GET /api/translate/parse-review/{task_id}/results
        """
        task, parse_file, error_response = self.get_task_and_file(request, task_id)
        if error_response:
            return error_response
        
        if task.status != 'pending':
            return Response(
                {'error': '待办任务已完成或已取消'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 从缓存获取解析结果
        from project.apps.translate.services.parse_review_service import ParseReviewService
        parse_result = ParseReviewService.get_parse_result(parse_file.file_id)
        
        if parse_result is None:
            return Response(
                {'error': '解析结果不存在或已过期，请重新解析'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 去除 formatted_data 中每个条目的 formatted 和 edited_formatted 末尾的换行符
        if 'formatted_data' in parse_result:
            for entry in parse_result['formatted_data']:
                if 'formatted' in entry:
                    entry['formatted'] = entry['formatted'].rstrip() if entry['formatted'] else ''
                if 'edited_formatted' in entry:
                    entry['edited_formatted'] = entry['edited_formatted'].rstrip() if entry['edited_formatted'] else ''
        
        return Response(parse_result, status=status.HTTP_200_OK)


class ParseReviewReparseView(ParseReviewViewSet):
    """重解析单个条目"""
    
    def post(self, request, task_id):
        """重解析单个条目
        
        POST /api/parse-review/{task_id}/reparse
        Body: {"entry_uuid": "...", "selected_key": "..."}
        """
        task, parse_file, error_response = self.get_task_and_file(request, task_id)
        if error_response:
            return error_response
        
        entry_uuid = request.data.get('entry_uuid')
        selected_key = request.data.get('selected_key')
        
        if not entry_uuid or not selected_key:
            return Response(
                {'error': '缺少必要参数：entry_uuid 和 selected_key'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 从缓存获取解析结果
        from project.apps.translate.services.parse_review_service import ParseReviewService
        parse_result = ParseReviewService.get_parse_result(parse_file.file_id)
        
        if parse_result is None:
            return Response(
                {'error': '解析结果不存在或已过期'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 查找对应的条目
        formatted_data = parse_result.get('formatted_data', [])
        target_entry = None
        for entry in formatted_data:
            if entry.get('uuid') == entry_uuid:
                target_entry = entry
                break
        
        if not target_entry:
            return Response(
                {'error': '未找到对应的条目'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 获取原始数据
        original_row = target_entry.get('original_row')
        if not original_row:
            return Response(
                {'error': '条目缺少原始数据，无法重解析'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 执行重解析
        try:
            owner_id = request.user.id
            config = get_user_config(request.user)
            parsed_entry = single_parse_transaction(original_row, owner_id, config, selected_key)
            formatted = FormatData.format_instance(parsed_entry, config=config)
            
            # 更新缓存
            ParseReviewService.update_entry_formatted(parse_file.file_id, entry_uuid, formatted)
            
            # 返回更新后的结果
            updated_result = ParseReviewService.get_parse_result(parse_file.file_id)
            updated_entry = None
            for entry in updated_result.get('formatted_data', []):
                if entry.get('uuid') == entry_uuid:
                    updated_entry = entry
                    break
            
            formatted_result = updated_entry.get('formatted') if updated_entry else formatted
            edited_formatted_result = updated_entry.get('edited_formatted') if updated_entry else formatted
            # 去除末尾的换行符
            formatted_result = formatted_result.rstrip() if formatted_result else ''
            edited_formatted_result = edited_formatted_result.rstrip() if edited_formatted_result else ''
            
            return Response({
                'uuid': entry_uuid,
                'formatted': formatted_result,
                'edited_formatted': edited_formatted_result,
                'selected_expense_key': selected_key,
                'expense_candidates_with_score': parsed_entry.get('expense_candidates_with_score', [])
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(e)
            return Response(
                {'error': f'重解析失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ParseReviewEditView(ParseReviewViewSet):
    """更新编辑内容"""
    
    def put(self, request, task_id, uuid):
        """更新编辑内容
        
        PUT /api/parse-review/{task_id}/entries/{uuid}/edit
        Body: {"edited_formatted": "..."}
        """
        task, parse_file, error_response = self.get_task_and_file(request, task_id)
        if error_response:
            return error_response
        
        edited_formatted = request.data.get('edited_formatted')
        if edited_formatted is None:
            return Response(
                {'error': '缺少必要参数：edited_formatted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 更新缓存
        from project.apps.translate.services.parse_review_service import ParseReviewService
        success = ParseReviewService.update_entry_edited_formatted(
            parse_file.file_id, uuid, edited_formatted
        )
        
        if not success:
            return Response(
                {'error': '更新编辑内容失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # 返回更新后的结果
        updated_result = ParseReviewService.get_parse_result(parse_file.file_id)
        updated_entry = None
        for entry in updated_result.get('formatted_data', []):
            if entry.get('uuid') == uuid:
                updated_entry = entry
                break
        
        return Response({
            'uuid': uuid,
            'edited_formatted': updated_entry.get('edited_formatted') if updated_entry else edited_formatted
        }, status=status.HTTP_200_OK)


class ParseReviewConfirmView(ParseReviewViewSet):
    """确认写入"""
    
    def post(self, request, task_id):
        """确认写入
        
        POST /api/translate/parse-review/{task_id}/confirm
        """
        task, parse_file, error_response = self.get_task_and_file(request, task_id)
        if error_response:
            return error_response
        
        if task.status != 'pending':
            return Response(
                {'error': '待办任务已完成或已取消'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 从缓存获取最终结果
        from project.apps.translate.services.parse_review_service import ParseReviewService
        from project.apps.translate.utils.beancount_validator import BeancountValidator
        from project.utils.file import BeanFileManager
        
        final_entries = ParseReviewService.get_final_result(parse_file.file_id)
        
        if not final_entries:
            return Response(
                {'error': '解析结果不存在或已过期，请重新解析'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 合并所有条目
        formatted_text = '\n\n'.join([
            entry['formatted'].rstrip() for entry in final_entries
        ])
        
        # 进行 Beancount 语法校验
        is_valid, error_message, _ = BeancountValidator.validate_entries(formatted_text)
        
        if not is_valid:
            return Response(
                {'error': f'Beancount 语法错误: {error_message}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 写入文件
        try:
            original_filename = parse_file.file.name
            bean_file_path = BeanFileManager.get_bean_file_path(request.user, original_filename)
            
            with open(bean_file_path, 'w', encoding='utf-8') as f:
                f.write(formatted_text)
            
            # 更新状态
            parse_file.status = 'parsed'
            parse_file.save()
            
            task.status = 'completed'
            task.save()
            
            # 删除缓存（可选，也可以保留一段时间）
            # ParseReviewService.delete_parse_result(parse_file.file_id)
            
            return Response({
                'message': '确认写入成功',
                'file_id': parse_file.file_id
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"确认写入失败: {str(e)}", exc_info=True)
            return Response(
                {'error': f'写入文件失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ParseReviewReparseAllView(ParseReviewViewSet):
    """重新解析所有条目"""
    
    def post(self, request, task_id):
        """重新解析所有条目
        
        POST /api/parse-review/{task_id}/reparse-all
        """
        task, parse_file, error_response = self.get_task_and_file(request, task_id)
        if error_response:
            return error_response
        
        if task.status != 'pending':
            return Response(
                {'error': '待办任务已完成或已取消'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 重新执行解析任务（相当于在文件管理中再次解析）
        from project.apps.translate.tasks import parse_single_file_task
        from project.utils.tools import get_user_config
        
        try:
            # 更新文件状态为待解析
            parse_file.status = 'pending'
            parse_file.save()
            
            # 创建解析任务（审核模式）
            config = get_user_config(request.user)
            args = {
                'write': False,  # 审核模式
                'cmb_credit_ignore': True,
                'boc_debit_ignore': True,
                'password': None,
                'balance': False,
                'isCSVOnly': False
            }
            
            # 异步执行解析任务
            parse_single_file_task.delay(parse_file.file_id, request.user.id, args)
            
            return Response({
                'message': '重新解析任务已提交',
                'file_id': parse_file.file_id
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            logger.error(f"重新解析失败: {str(e)}", exc_info=True)
            return Response(
                {'error': f'重新解析失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
