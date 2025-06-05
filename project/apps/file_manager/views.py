from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import BillFile
from .serializers import BillFileSerializer
from project.utils.minio_utils import MinIOClient
from project.utils.file import calculate_file_hash
from maps.permissions import IsOwnerOrAdminReadWriteOnly
from maps.filters import CurrentUserFilterBackend
from rest_framework_simplejwt.authentication import JWTAuthentication
import logging

logger = logging.getLogger(__name__)

class BillFileViewSet(viewsets.ModelViewSet):
    queryset = BillFile.objects.filter(is_active=True)
    serializer_class = BillFileSerializer
    # permission_classes = [IsAuthenticated]
    permission_classes = [IsOwnerOrAdminReadWriteOnly]
    # filter_backends = [CurrentUserFilterBackend]
    http_method_names = ['get', 'post', 'delete']  # 禁用put/patch
    authentication_classes = [JWTAuthentication]

    # def get_queryset(self):
    #     """确保用户只能访问自己的文件"""
    #     return self.queryset.filter(user=self.request.user)

    def perform_destroy(self, instance):
        """软删除而非物理删除"""
        instance.is_active = False
        instance.save()

    def create(self, request):
        """文件上传处理"""
        if 'file' not in request.FILES:
            return Response(
                {"error": "No file provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        file_obj = request.FILES['file']
        minio_client = MinIOClient()

        try:
            # 计算文件哈希
            file_hash = calculate_file_hash(file_obj)
            
            # 检查文件是否已存在（包括已软删除的）
            existing_file = BillFile.objects.filter(
                owner=request.user,
                file_hash=file_hash
            ).first()
        
            if existing_file:
                # 如果文件存在但被软删除，则重新激活
                if not existing_file.is_active:
                    existing_file.is_active = True
                    existing_file.original_name = file_obj.name  # 更新文件名（如果需要）
                    existing_file.save()
                
                return Response(
                    {
                        "message": "文件已存在并已重新激活",
                        "existing_file": BillFileSerializer(existing_file).data
                    },
                    status=status.HTTP_200_OK
                )

            # 上传到MinIO
            object_name = minio_client.upload_file(
                bucket_name="beancount-trans",
                file_obj=file_obj,
                file_name=file_obj.name
            )

            # 保存到数据库
            bill_file = BillFile.objects.create(
                owner=request.user,
                original_name=file_obj.name,
                storage_path=object_name,
                file_size=file_obj.size,
                file_hash=file_hash
            )

            serializer = self.get_serializer(bill_file)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"File upload failed: {str(e)}", exc_info=True)
            return Response(
                {"error": "文件上传失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """文件下载"""
        bill_file = get_object_or_404(
            BillFile, 
            pk=pk, 
            owner=request.user,
            is_active=True
        )
        minio_client = MinIOClient()

        try:
            file_stream = minio_client.get_file(
                bucket_name="beancount-trans",
                object_name=bill_file.storage_path
            )
            
            response = Response(file_stream.getvalue())
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = (
                f'attachment; filename="{bill_file.original_name}"'
            )
            return response

        except Exception as e:
            logger.error(f"File download failed: {str(e)}", exc_info=True)
            return Response(
                {"error": "文件下载失败"},
                status=status.HTTP_404_NOT_FOUND
            )
