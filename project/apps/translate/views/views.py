import logging
from django.shortcuts import render
from django.contrib.auth import get_user_model
from project.utils.exceptions import UnsupportedFileTypeError, DecryptionError
from project.utils.token import get_token_user_id
from project.utils.tools import get_user_config
from rest_framework.views import APIView
from translate.serializers import AnalyzeSerializer, FormatConfigSerializer
from translate.services.analyze_service import AnalyzeService
from rest_framework.response import Response
from rest_framework import status

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

# from project.utils.tools import get_user_config
from translate.models import FormatConfig
from maps.permissions import IsOwnerOrAdminReadWriteOnly
from rest_framework.permissions import AllowAny


User = get_user_model()
logger = logging.getLogger(__name__)


class SingleBillAnalyzeView(APIView):
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


# 上传文件
class UploadFileView(APIView):
    pass


# 多账单解析
class MultipleBillAnalyzeView(APIView):
    pass


# 单条目解析(AI解析反馈)
class SingleEntryAnalyzeView(APIView):
    pass


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


class UnifiedAnalyzeView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        # 1. 判断请求类型
        # 例如通过参数 distinguish_type: 'single'/'multi'/'entry'
        req_type = request.data.get('type', 'single')
        if req_type == 'single':
            return SingleBillAnalyzeView().post(request)
        elif req_type == 'multi':
            return MultipleBillAnalyzeView().post(request)
        elif req_type == 'entry':
            return SingleEntryAnalyzeView().post(request)
        else:
            return Response({'error': '未知解析类型'}, status=400)