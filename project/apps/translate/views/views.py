# project/apps/translate/views/views.py
import logging
import uuid
import json
import time
from celery.result import GroupResult
from celery import group
from django.core.cache import cache
from django.shortcuts import render
from django.contrib.auth import get_user_model
from project.utils.exceptions import UnsupportedFileTypeError, DecryptionError
from project.utils.token import get_token_user_id
from project.utils.tools import get_user_config
from project.apps.common.permissions import IsOwnerOrAdminReadWriteOnly
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
    """用户个人配置接口"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOwnerOrAdminReadWriteOnly]

    def get(self, request):
        """获取当前用户配置"""
        config = FormatConfig.get_user_config(request.user)
        serializer = FormatConfigSerializer(config)
        return Response(serializer.data)

    def put(self, request):
        """更新当前用户配置"""
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

        # 更新文件状态为待处理
        for file_id in file_ids:
            parse_file, _ = ParseFile.objects.get_or_create(file_id=file_id)
            parse_file.status = 'pending'
            parse_file.save()

        # 创建任务组
        tasks = []
        args = {
            'write': True,
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

        return Response({
            'task_group_id': task_group_id,
            'status': 'pending'
        }, status=status.HTTP_202_ACCEPTED)


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
            if task_status['status'] in ['success', 'failed']:
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
