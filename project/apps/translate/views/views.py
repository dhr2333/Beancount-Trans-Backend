# project/apps/translate/views/views.py
import logging
import uuid
import json
import time
import os
from typing import Dict, Optional
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
from project.apps.translate.services.parse.installment_expander import (
    expand_parsed_entry,
    pick_reparse_slice,
    resolve_reparse_entry,
)
from project.apps.translate.services.alipay_refund_peer import resolve_refund_peer_for_row
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
                    formatted_text = formatted_data.get("formatted") or ''
                    if isinstance(formatted_text, str):
                        formatted_text = formatted_text.rstrip()
                    results.append({
                        "id": formatted_data.get("id"),
                        "uuid": formatted_data.get("uuid") or formatted_data.get("id"),
                        "formatted": formatted_text,
                        "edited_formatted": formatted_data.get("edited_formatted") or formatted_text,
                        "ai_choose": formatted_data.get("selected_expense_key"),
                        "ai_candidates": formatted_data.get("expense_candidates_with_score", []),
                        "counterparty": formatted_data.get("counterparty", ""),
                        "commodity": formatted_data.get("commodity", ""),
                        "payment_method": formatted_data.get("payment_method", ""),
                        "transaction_type": formatted_data.get("transaction_type", ""),
                        "installment_role": formatted_data.get("installment_role"),
                        "installment_period": formatted_data.get("installment_period"),
                        "tag_details": formatted_data.get("tag_details") or [],
                        "original_row": formatted_data.get("original_row") or {},
                    })
                else:
                    results.append({
                        "id": formatted_data.get("id") if hasattr(formatted_data, 'get') else None,
                        "formatted": formatted_data,
                        "edited_formatted": formatted_data,
                        "ai_choose": None,
                        "ai_candidates": [],
                    })
            response_data = {
            "results": results,
            "summary": {"count": len(results)},
            "status": "success"
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except DecryptionError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except UnsupportedFileTypeError as e:
            return Response({'error': str(e)}, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
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
        mapping_type = serializer.validated_data.get('mapping_type') or 'expense'
        cache_key = entry_id
        cache_data = cache.get(cache_key)

        if not cache_data:
            return Response({'error': '缓存已过期或记录不存在'}, status=status.HTTP_404_NOT_FOUND)

        original_row = cache_data['original_row']
        cached_parsed = cache_data.get('parsed_entry') or {}
        owner_id = get_token_user_id(request)
        user = User.objects.get(id=owner_id)
        config = get_user_config(user)
        expense_selected_key = selected_key
        if mapping_type == 'asset':
            expense_selected_key = cached_parsed.get('selected_expense_key') or None
            if expense_selected_key == '':
                expense_selected_key = None
        # 重新解析交易记录
        try:
            refund_peer = resolve_refund_peer_for_row(
                original_row, user, owner_id, config, expense_selected_key
            )
            base_parsed = single_parse_transaction(
                original_row, owner_id, config, expense_selected_key, refund_peer=refund_peer
            )
            parsed_entry = resolve_reparse_entry(
                base_parsed,
                original_row,
                installment_role=cached_parsed.get('installment_role'),
                installment_period=cached_parsed.get('installment_period'),
            )

            formatted = FormatData.format_instance(parsed_entry, config=config)

            # 更新缓存
            cache.set(cache_key, {
                "parsed_entry": parsed_entry,
                "original_row": original_row,
            }, timeout=3600)
            response_ai_choose = (
                cached_parsed.get('selected_expense_key')
                if mapping_type == 'asset'
                else selected_key
            )
            if parsed_entry.get('installment_role') == 'installment':
                response_ai_choose = None
            formatted_text = formatted.rstrip() if formatted else ''
            return Response({
                "id": entry_id,
                "uuid": entry_id,
                "formatted": formatted_text,
                "edited_formatted": formatted_text,
                "ai_choose": response_ai_choose,
                "ai_candidates": parsed_entry.get('expense_candidates_with_score') or [],
                "counterparty": original_row.get("counterparty", ""),
                "commodity": original_row.get("commodity", ""),
                "payment_method": original_row.get("payment_method", ""),
                "transaction_type": original_row.get("transaction_type", ""),
                "installment_role": parsed_entry.get("installment_role"),
                "installment_period": parsed_entry.get("installment_period"),
                "tag_details": parsed_entry.get("tag_details") or [],
                "original_row": original_row,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(e)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ValidateEntryView(APIView):
    """单条 Beancount 语法校验（不阻断保存，仅返回 warning）"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        edited_formatted = request.data.get('edited_formatted')
        if edited_formatted is None:
            return Response(
                {'error': '缺少必要参数：edited_formatted'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from project.apps.translate.utils.beancount_validator import BeancountValidator

        response_data = {'edited_formatted': edited_formatted}
        is_valid, validation_error = BeancountValidator.validate_single_entry(
            edited_formatted or ''
        )
        if not is_valid and validation_error:
            response_data['validation_warning'] = validation_error
        return Response(response_data, status=status.HTTP_200_OK)


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
            'password': request.data.get('password') or None,
        }

        for file_id in file_ids:
            # 如果提供了 passwords 字典，为每个文件分配对应的密码
            passwords = request.data.get('passwords', {})
            file_args = args.copy()
            if str(file_id) in passwords:
                file_args['password'] = passwords[str(file_id)]
                
            task = parse_single_file_task.s(file_id, request.user.id, file_args)
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
            # 审核模式：返回当前用户全局唯一的条目审核待办ID
            from project.apps.translate.services.entry_review_queue_service import EntryReviewQueueService
            review_task = EntryReviewQueueService.get_or_create_task(request.user)
            response_data['entry_review_task_id'] = review_task.id

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
        from project.apps.translate.services.entry_review_queue_service import (
            EntryReviewQueueService,
        )

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
                BeanFileManager.clear_bean_file(request.user, file_obj.get_bean_relative_path())
                
                # 从用户级统一审核队列中移除该文件的所有引用
                # 队列为空时把条目审核待办置为未激活，便于用户重新解析文件
                EntryReviewQueueService.remove_file(request.user.id, file_id)
                EntryReviewQueueService.deactivate_if_empty(request.user)

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


class EntryReviewViewSet(APIView):
    """统一条目审核视图基类

    每个用户全局唯一一个条目审核待办，所有审核接口以 file_id 定位具体文件，
    待审核条目集合由 EntryReviewQueueService 管理。
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_review_task(self, request):
        """返回当前用户的统一条目审核待办（可能为 None）"""
        from django.contrib.auth import get_user_model
        content_type = ContentType.objects.get_for_model(get_user_model())
        return ScheduledTask.objects.filter(
            task_type='entry_review',
            content_type=content_type,
            object_id=request.user.id,
        ).first()

    def get_parse_file(self, request, file_id):
        """校验 file_id 归属当前用户；返回 (parse_file, error_response)"""
        parse_file = ParseFile.objects.filter(file_id=file_id).select_related('file').first()
        if parse_file is None:
            return None, Response({'error': '文件不存在'}, status=status.HTTP_404_NOT_FOUND)
        if parse_file.file.owner != request.user:
            return None, Response({'error': '无权访问该文件'}, status=status.HTTP_403_FORBIDDEN)
        return parse_file, None

    def ensure_editable(self, request, parse_file):
        """校验：待办处于 pending、文件处于 pending_review、未过期；返回 error_response 或 None"""
        from project.apps.translate.services.parse_review_service import ParseReviewService
        task = self.get_review_task(request)
        if task is None or task.status != 'pending':
            return Response({'error': '待办任务已完成或已取消'}, status=status.HTTP_400_BAD_REQUEST)
        if parse_file.status != 'pending_review':
            return Response({'error': '该文件当前不可审核'}, status=status.HTTP_400_BAD_REQUEST)
        cached_data = ParseReviewService.get_parse_result(parse_file.file_id)
        if ParseReviewService.is_review_expired(cached_data, None):
            return Response({'error': '解析待办已过期，系统将自动写入'}, status=status.HTTP_400_BAD_REQUEST)
        return None


def _serialize_parse_review_entry(
    entry_uuid: str,
    updated_entry: Optional[dict],
    formatted: str,
    selected_key: Optional[str],
    parsed_entry: dict,
) -> dict:
    """构造单条解析审核重解析 API 响应字段。"""
    from project.apps.translate.services.parse_review_service import ParseReviewService

    formatted_result = updated_entry.get('formatted') if updated_entry else formatted
    edited_formatted_result = (
        updated_entry.get('edited_formatted') if updated_entry else formatted
    )
    formatted_result = formatted_result.rstrip() if formatted_result else ''
    edited_formatted_result = edited_formatted_result.rstrip() if edited_formatted_result else ''
    is_installment = parsed_entry.get('installment_role') == 'installment'
    tag_payload = (
        ParseReviewService.entry_response_payload(updated_entry)
        if updated_entry
        else {
            'tag_details': ParseReviewService.apply_tag_overrides(
                parsed_entry.get('tag_details', []),
                ParseReviewService.default_tag_overrides(),
            ),
            'tag_overrides': ParseReviewService.default_tag_overrides(),
        }
    )
    return {
        'uuid': entry_uuid,
        'formatted': formatted_result,
        'edited_formatted': edited_formatted_result,
        'selected_expense_key': None if is_installment else selected_key,
        'expense_candidates_with_score': parsed_entry.get('expense_candidates_with_score', []),
        **tag_payload,
    }


def _reparse_review_entry(
    *,
    file_id: int,
    entry: dict,
    owner_id: int,
    config,
    user,
    selected_key: Optional[str] = None,
    mapping_type: str = 'expense',
) -> Optional[dict]:
    """重解析单条审核条目并写回 Redis，返回 API 响应字段。"""
    from project.apps.translate.services.parse_review_service import ParseReviewService

    entry_uuid = entry.get('uuid')
    original_row = entry.get('original_row')
    if not entry_uuid or not original_row:
        return None

    expense_selected_key = selected_key
    if mapping_type == 'asset':
        expense_selected_key = entry.get('selected_expense_key') or None
        if expense_selected_key == '':
            expense_selected_key = None

    refund_peer = resolve_refund_peer_for_row(
        original_row, user, owner_id, config, expense_selected_key
    )
    base_parsed = single_parse_transaction(
        original_row, owner_id, config, expense_selected_key, refund_peer=refund_peer
    )
    base_parsed['_original_row'] = original_row
    expanded = expand_parsed_entry(base_parsed, set())
    parsed_entry = pick_reparse_slice(
        expanded,
        entry.get('installment_role'),
        entry.get('installment_period'),
    )
    formatted = FormatData.format_instance(parsed_entry, config=config)
    is_installment = parsed_entry.get('installment_role') == 'installment'
    if mapping_type == 'asset':
        stored_expense_key = parsed_entry.get('selected_expense_key')
    else:
        stored_expense_key = expense_selected_key
    ParseReviewService.update_entry_formatted(
        file_id,
        entry_uuid,
        formatted,
        tag_details=parsed_entry.get('tag_details', []),
        selected_expense_key=None if is_installment else stored_expense_key,
        expense_candidates_with_score=parsed_entry.get(
            'expense_candidates_with_score', []
        ),
    )

    if parsed_entry.get('installment_role') == 'purchase' and len(expanded) > 1:
        cached_after = ParseReviewService.get_parse_result_migrated(file_id) or {}
        for sibling in ParseReviewService.iter_same_order_installment_entries(
            cached_after.get('formatted_data') or [],
            original_row,
            entry_uuid,
        ):
            sib_entry = pick_reparse_slice(
                expanded,
                'installment',
                sibling.get('installment_period'),
            )
            sib_formatted = FormatData.format_instance(sib_entry, config=config)
            ParseReviewService.update_entry_formatted(
                file_id,
                sibling.get('uuid'),
                sib_formatted,
                tag_details=sib_entry.get('tag_details', []),
                selected_expense_key=None,
                expense_candidates_with_score=[],
            )

    updated_result = ParseReviewService.get_parse_result(file_id)
    updated_entry = None
    if updated_result:
        for cached_entry in updated_result.get('formatted_data', []):
            if cached_entry.get('uuid') == entry_uuid:
                updated_entry = cached_entry
                break

    response_selected_key = (
        parsed_entry.get('selected_expense_key')
        if mapping_type == 'asset'
        else expense_selected_key
    )
    return _serialize_parse_review_entry(
        entry_uuid,
        updated_entry,
        formatted,
        response_selected_key,
        parsed_entry,
    )


def _propagate_mapping_to_batch(
    *,
    file_id: int,
    owner_id: int,
    config,
    user,
    mapping_key: str,
    exclude_uuid: str,
    mapping_type: str = 'expense',
) -> list:
    """将新建/更新的映射套用到同批匹配条目（不强制 selected_key）。"""
    from project.apps.translate.services.parse_review_service import ParseReviewService

    cached = ParseReviewService.get_parse_result_migrated(file_id) or {}
    propagated = []
    for entry in cached.get('formatted_data') or []:
        entry_uuid = entry.get('uuid')
        if not entry_uuid or entry_uuid == exclude_uuid:
            continue
        if entry.get('installment_role') == 'installment':
            continue
        if ParseReviewService.entry_postings_manually_edited(entry):
            continue
        if not ParseReviewService.row_matches_mapping_key(
            entry.get('original_row'), mapping_key, mapping_type=mapping_type
        ):
            continue
        payload = _reparse_review_entry(
            file_id=file_id,
            entry=entry,
            owner_id=owner_id,
            config=config,
            user=user,
            selected_key=None,
            mapping_type=mapping_type,
        )
        if payload:
            propagated.append(payload)
    return propagated


class EntryReviewResultsView(EntryReviewViewSet):
    """获取用户级统一审核结果"""

    def get(self, request):
        """获取待审核条目列表

        GET /api/translate/entry-review/results
        """
        from project.apps.translate.services.parse_review_service import ParseReviewService
        from project.apps.translate.services.entry_review_queue_service import EntryReviewQueueService

        config = get_user_config(request.user)

        # 收集队列涉及的全部 file_id（去重）
        file_ids = []
        seen = set()
        for ref in EntryReviewQueueService.list_refs(request.user.id):
            file_id = ref.get('file_id')
            if file_id is None or file_id in seen:
                continue
            seen.add(file_id)
            file_ids.append(file_id)

        # 逐文件回填 tag_details，并做 uuid 迁移
        for file_id in file_ids:
            data = ParseReviewService.get_parse_result_migrated(file_id)
            if data is None:
                continue
            if ParseReviewService.backfill_tag_details_in_data(
                data, request.user.id, config, user=request.user
            ):
                ParseReviewService.save_parse_result(
                    file_id, data, timeout=ParseReviewService._ttl_for_resave(file_id)
                )

        # 条目副本，可安全修改
        entries = EntryReviewQueueService.list_entries(request.user.id)
        for entry in entries:
            ParseReviewService.normalize_entry_tag_fields(entry)
            if 'formatted' in entry:
                entry['formatted'] = entry['formatted'].rstrip() if entry['formatted'] else ''
            if 'edited_formatted' in entry:
                entry['edited_formatted'] = entry['edited_formatted'].rstrip() if entry['edited_formatted'] else ''
            entry['tag_details'] = ParseReviewService.get_effective_tag_details(entry)

        return Response({
            'entries': entries,
            'entry_count': len(entries),
            'review_expires_at': EntryReviewQueueService.earliest_expires_at(request.user.id),
        }, status=status.HTTP_200_OK)


class EntryReviewReparseView(EntryReviewViewSet):
    """重解析单个条目"""

    def post(self, request):
        """重解析单个条目

        POST /api/translate/entry-review/reparse
        Body: {"file_id": ..., "entry_uuid": "...", "selected_key": "...", "mapping_type": "expense"}
        """
        file_id = request.data.get('file_id')
        parse_file, error_response = self.get_parse_file(request, file_id)
        if error_response:
            return error_response

        editable_error = self.ensure_editable(request, parse_file)
        if editable_error:
            return editable_error

        entry_uuid = request.data.get('entry_uuid')
        selected_key = request.data.get('selected_key')
        mapping_type = request.data.get('mapping_type') or 'expense'
        if mapping_type not in ('expense', 'income', 'asset'):
            mapping_type = 'expense'

        if not entry_uuid or not selected_key:
            return Response(
                {'error': '缺少必要参数：entry_uuid 和 selected_key'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 从缓存获取解析结果
        from project.apps.translate.services.parse_review_service import ParseReviewService
        parse_result = ParseReviewService.get_parse_result_migrated(file_id)

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
            payload = _reparse_review_entry(
                file_id=file_id,
                entry=target_entry,
                owner_id=owner_id,
                config=config,
                user=request.user,
                selected_key=selected_key,
                mapping_type=mapping_type,
            )
            if payload is None:
                return Response(
                    {'error': '重解析失败'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            propagated_entries = _propagate_mapping_to_batch(
                file_id=file_id,
                owner_id=owner_id,
                config=config,
                user=request.user,
                mapping_key=selected_key,
                exclude_uuid=entry_uuid,
                mapping_type=mapping_type,
            )

            return Response({
                **payload,
                'propagated_entries': propagated_entries,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(e)
            return Response(
                {'error': f'重解析失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EntryReviewEditView(EntryReviewViewSet):
    """更新编辑内容"""

    def put(self, request, uuid):
        """更新编辑内容

        PUT /api/translate/entry-review/entries/{uuid}/edit
        Body: {"file_id": ..., "edited_formatted": "..."}
        """
        file_id = request.data.get('file_id')
        parse_file, error_response = self.get_parse_file(request, file_id)
        if error_response:
            return error_response

        editable_error = self.ensure_editable(request, parse_file)
        if editable_error:
            return editable_error

        edited_formatted = request.data.get('edited_formatted')
        if edited_formatted is None:
            return Response(
                {'error': '缺少必要参数：edited_formatted'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 更新缓存（先迁移 uuid，再解析路径中的占位符）
        from project.apps.translate.services.parse_review_service import ParseReviewService
        from project.apps.translate.utils.beancount_validator import BeancountValidator

        migrated = ParseReviewService.get_parse_result_migrated(file_id)
        if migrated is None:
            return Response(
                {'error': '解析结果不存在或已过期，请重新解析'},
                status=status.HTTP_404_NOT_FOUND,
            )

        entry_uuid = uuid
        if uuid in ('null', 'undefined', 'None'):
            fd = migrated.get('formatted_data') or []
            if len(fd) == 1 and fd[0].get('uuid'):
                entry_uuid = fd[0]['uuid']

        success = ParseReviewService.update_entry_edited_formatted(
            file_id, entry_uuid, edited_formatted
        )

        if not success:
            return Response(
                {'error': '更新编辑内容失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 返回更新后的结果
        updated_result = ParseReviewService.get_parse_result(file_id)
        updated_entry = None
        for entry in updated_result.get('formatted_data', []):
            if entry.get('uuid') == entry_uuid:
                updated_entry = entry
                break

        content_to_validate = updated_entry.get('edited_formatted') if updated_entry else edited_formatted
        response_data = {
            'uuid': entry_uuid,
            'edited_formatted': content_to_validate,
        }
        # 保存后对单条内容做校验，作为即时反馈（不阻断保存）
        is_valid, validation_error = BeancountValidator.validate_single_entry(content_to_validate or '')
        if not is_valid and validation_error:
            response_data['validation_warning'] = validation_error

        return Response(response_data, status=status.HTTP_200_OK)


class EntryReviewTagsView(EntryReviewViewSet):
    """更新条目标签（添加/移除）"""

    def patch(self, request, uuid):
        """PATCH /api/translate/entry-review/entries/{uuid}/tags

        Body: {"file_id": ..., "action": "add|remove", "tag_path": "Category/EDUCATION"}
        """
        file_id = request.data.get('file_id')
        parse_file, error_response = self.get_parse_file(request, file_id)
        if error_response:
            return error_response

        editable_error = self.ensure_editable(request, parse_file)
        if editable_error:
            return editable_error

        action = request.data.get('action')
        tag_path = request.data.get('tag_path')
        if action not in ('add', 'remove') or not tag_path:
            return Response(
                {'error': '缺少必要参数：action（add/remove）与 tag_path'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from project.apps.translate.services.parse_review_service import ParseReviewService

        migrated = ParseReviewService.get_parse_result_migrated(file_id)
        if migrated is None:
            return Response(
                {'error': '解析结果不存在或已过期，请重新解析'},
                status=status.HTTP_404_NOT_FOUND,
            )

        entry_uuid = uuid
        if uuid in ('null', 'undefined', 'None'):
            fd = migrated.get('formatted_data') or []
            if len(fd) == 1 and fd[0].get('uuid'):
                entry_uuid = fd[0]['uuid']

        result = ParseReviewService.update_entry_tags(
            file_id,
            entry_uuid,
            action,
            tag_path,
        )
        if result is None:
            return Response(
                {'error': '更新标签失败或未找到条目'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result, status=status.HTTP_200_OK)


class EntryReviewPreviewSyncView(EntryReviewViewSet):
    """预览批量同步（以预览文本为真源，支持删条）"""

    def put(self, request):
        """PUT /api/translate/entry-review/preview-sync

        Body: {"file_id": ..., "entries": [{"uuid": "...", "edited_formatted": "..."}]}
        """
        file_id = request.data.get('file_id')
        parse_file, error_response = self.get_parse_file(request, file_id)
        if error_response:
            return error_response

        editable_error = self.ensure_editable(request, parse_file)
        if editable_error:
            return editable_error

        entries = request.data.get('entries')
        if not isinstance(entries, list):
            return Response(
                {'error': '缺少必要参数：entries'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from project.apps.translate.services.parse_review_service import ParseReviewService
        from project.apps.translate.utils.beancount_validator import BeancountValidator

        migrated = ParseReviewService.get_parse_result_migrated(file_id)
        if migrated is None:
            return Response(
                {'error': '解析结果不存在或已过期，请重新解析'},
                status=status.HTTP_404_NOT_FOUND,
            )

        sync_result = ParseReviewService.sync_entries_from_preview(
            file_id,
            entries,
        )
        if sync_result is None:
            return Response(
                {'error': '预览同步失败，请检查条目 uuid 是否有效'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        formatted_data = sync_result['formatted_data']
        for entry in formatted_data:
            if 'formatted' in entry and entry['formatted']:
                entry['formatted'] = entry['formatted'].rstrip()
            if 'edited_formatted' in entry and entry['edited_formatted']:
                entry['edited_formatted'] = entry['edited_formatted'].rstrip()

        validation_warnings: Dict[str, str] = {}
        for entry in formatted_data:
            content = entry.get('edited_formatted') or ''
            is_valid, validation_error = BeancountValidator.validate_single_entry(content)
            if not is_valid and validation_error:
                entry_uuid = entry.get('uuid')
                if entry_uuid:
                    validation_warnings[entry_uuid] = validation_error

        return Response(
            {
                'formatted_data': formatted_data,
                'removed_count': sync_result['removed_count'],
                'validation_warnings': validation_warnings,
            },
            status=status.HTTP_200_OK,
        )


class EntryReviewConfirmView(EntryReviewViewSet):
    """确认写入（用户级统一审核）"""

    def post(self, request):
        """确认写入

        POST /api/translate/entry-review/confirm
        """
        from project.apps.translate.services.parse_review_service import ParseReviewService
        from project.apps.translate.services.entry_review_queue_service import EntryReviewQueueService
        from project.apps.translate.utils.beancount_validator import BeancountValidator
        from project.utils.file import BeanFileManager

        task = self.get_review_task(request)
        if task is None or task.status != 'pending':
            return Response(
                {'error': '待办任务已完成或已取消'},
                status=status.HTTP_400_BAD_REQUEST
            )

        refs = EntryReviewQueueService.list_refs(request.user.id)
        if not refs:
            return Response(
                {'error': '待审核队列为空'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 按 file_id 分组并保持顺序
        file_ids = []
        seen = set()
        for ref in refs:
            file_id = ref.get('file_id')
            if file_id is None or file_id in seen:
                continue
            seen.add(file_id)
            file_ids.append(file_id)

        # 先校验全部文件，全部通过后再写入
        validations = []  # 待写入文件：[{file_id, parse_file, text, entry_count}]
        error_entries = []  # 结构化错误条目
        pending_removal = []  # 无有效条目、待清理引用的 file_id
        for file_id in file_ids:
            parse_file, error_response = self.get_parse_file(request, file_id)
            if error_response:
                # 文件丢失：从队列移除该文件引用后跳过
                EntryReviewQueueService.remove_file(request.user.id, file_id)
                continue

            final_entries = ParseReviewService.get_final_result(file_id)
            if not final_entries:
                # 该文件无有效条目，记录待清理引用
                pending_removal.append(file_id)
                continue

            # 合并所有条目
            formatted_text = '\n\n'.join([
                entry['formatted'].rstrip() for entry in final_entries
            ])

            # 进行 Beancount 语法校验
            is_valid, error_message, _ = BeancountValidator.validate_entries(formatted_text)
            if not is_valid:
                # 逐条校验以定位错误条目
                entries_list = [entry['formatted'].rstrip() for entry in final_entries]
                _, _, error_entries_indices = BeancountValidator.validate_multiple_entries(entries_list)
                error_entries.extend([
                    {
                        'file_id': file_id,
                        'uuid': final_entries[idx]['uuid'],
                        'index': idx,
                        'error_message': msg or error_message,
                    }
                    for idx, msg in error_entries_indices
                ])
                continue

            validations.append({
                'file_id': file_id,
                'parse_file': parse_file,
                'text': formatted_text,
                'entry_count': len(final_entries),
            })

        # 只要有任何错误，不写入任何文件、不改状态
        if error_entries:
            return Response(
                {
                    'error': f'Beancount 语法错误: 共 {len(error_entries)} 条格式有误',
                    'error_entries': error_entries,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # 全部通过后再写入文件
        written_files = []
        try:
            for item in validations:
                parse_file = item['parse_file']
                bean_file_path = BeanFileManager.get_bean_file_path(
                    request.user, parse_file.file.name, parse_file.file.get_bean_dir()
                )
                with open(bean_file_path, 'w', encoding='utf-8') as f:
                    f.write(item['text'])

                parse_file.status = 'parsed'
                parse_file.save()

                written_files.append({
                    'file_id': item['file_id'],
                    'entry_count': item['entry_count'],
                })
        except Exception as e:
            logger.error(f"确认写入失败: {str(e)}", exc_info=True)
            return Response(
                {'error': f'写入文件失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 清理无有效条目的文件引用后清空队列并完成待办
        for file_id in pending_removal:
            EntryReviewQueueService.remove_file(request.user.id, file_id)
        EntryReviewQueueService.clear(request.user.id)
        EntryReviewQueueService.complete_task(request.user)

        return Response({
            'message': '确认写入成功',
            'files': written_files,
        }, status=status.HTTP_200_OK)


class ParseTaskStatusView(APIView):
    """查询单个 Celery 解析任务状态（与 task_status:{task_id} 缓存一致）"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        celery_task_id = request.query_params.get('task_id')
        if not celery_task_id:
            return Response(
                {'error': '缺少 task_id 参数'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task_status = cache.get(f'task_status:{celery_task_id}') or {'status': 'unknown'}
        file_id = task_status.get('file_id')
        if file_id is not None:
            file_obj = None
            try:
                from project.apps.file_manager.models import File
                file_obj = File.objects.filter(id=file_id, owner=request.user).first()
            except Exception:
                file_obj = None
            if file_obj is None:
                return Response(
                    {'error': '无权访问该任务'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        return Response({
            'task_id': celery_task_id,
            'file_id': file_id,
            'status': task_status.get('status', 'unknown'),
            'error': task_status.get('error'),
        }, status=status.HTTP_200_OK)


class EntryReviewReparseAllView(EntryReviewViewSet):
    """重新解析某文件的所有条目"""

    def post(self, request):
        """重新解析所有条目

        POST /api/translate/entry-review/reparse-all
        Body: {"file_id": ...}
        """
        file_id = request.data.get('file_id')
        parse_file, error_response = self.get_parse_file(request, file_id)
        if error_response:
            return error_response

        task = self.get_review_task(request)
        if task is None or task.status != 'pending':
            return Response(
                {'error': '待办任务已完成或已取消'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 重新执行解析任务（相当于在文件管理中再次解析）
        from project.apps.translate.tasks import parse_single_file_task

        try:
            # 更新文件状态为待解析
            parse_file.status = 'pending'
            parse_file.save()

            # 创建解析任务（审核模式）
            password = request.data.get('password') or None
            if password == '':
                password = None
            args = {
                'write': False,  # 审核模式
                'cmb_credit_ignore': True,
                'boc_debit_ignore': True,
                'password': password,
            }

            # 异步执行解析任务
            async_result = parse_single_file_task.delay(parse_file.file_id, request.user.id, args)
            cache.set(f'task_status:{async_result.id}', {
                'status': 'pending',
                'file_id': parse_file.file_id,
                'error': None,
            }, timeout=24 * 3600)

            return Response({
                'message': '重新解析任务已提交',
                'file_id': parse_file.file_id,
                'celery_task_id': async_result.id,
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            logger.error(f"重新解析失败: {str(e)}", exc_info=True)
            return Response(
                {'error': f'重新解析失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
