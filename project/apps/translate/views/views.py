# project/apps/translate/views/views.py
import logging
from django.core.cache import cache
from django.shortcuts import render
from django.contrib.auth import get_user_model
from project.utils.exceptions import UnsupportedFileTypeError, DecryptionError
from project.utils.token import get_token_user_id
from project.utils.tools import get_user_config
from translate.models import FormatConfig
from translate.serializers import AnalyzeSerializer, FormatConfigSerializer, ReparseSerializer
from translate.services.analyze_service import AnalyzeService
from maps.permissions import IsOwnerOrAdminReadWriteOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.permissions import AllowAny
from translate.utils import FormatData
from translate.services.parse.transaction_parser import single_parse_transaction


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
    def get_permissions(self):
        """动态权限控制"""
        if self.request.method == 'GET':  # GET请求允许匿名访问
            return [AllowAny()]
        else:  # PUT等写操作需要认证和所有权验证
            return [IsAuthenticated(), IsOwnerOrAdminReadWriteOnly()]
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
        owner_id = get_token_user_id(request)
        config = get_user_config(User.objects.get(id=owner_id))

        # 获取上传文件
        uploaded_file = request.FILES.get('trans', None)
        if not uploaded_file:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        # 创建服务并解析
        service = AnalyzeService(owner_id, config)
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
        APIView (_type_): _description_
    """
    pass
