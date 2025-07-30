import os
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from minio.error import S3Error
from project.apps.file_manager.models import Directory, File
from project.apps.file_manager.serializers import DirectorySerializer, FileSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from project.apps.maps.filters import CurrentUserFilterBackend
from project.apps.maps.permissions import IsOwnerOrAdminReadWriteOnly
from project.utils.file import generate_file_hash
from project.utils.minio import get_minio_client


class DirectoryViewSet(ModelViewSet):
    queryset = Directory.objects.all()
    serializer_class = DirectorySerializer
    permission_classes = [IsOwnerOrAdminReadWriteOnly]
    filter_backends = [CurrentUserFilterBackend]
    authentication_classes = [JWTAuthentication]

    @action(detail=True, methods=['get'])
    def contents(self, request, pk=None):
        directory = self.get_object()

        # 获取子目录
        subdirs = Directory.objects.filter(parent=directory)
        dir_serializer = DirectorySerializer(subdirs, many=True)

        # 获取文件
        files = File.objects.filter(directory=directory)
        file_serializer = FileSerializer(files, many=True)

        return Response({
            'directory': dir_serializer.data,
            'files': file_serializer.data,
            'id': directory.id
        })

    @action(detail=False, methods=['get'])
    def root_contents(self, request):
        # 获取当前用户的根目录（parent为null的目录）
        try:
            root_dir = Directory.objects.get(owner=request.user, parent__isnull=True)
        except Directory.DoesNotExist:
            root_dir = Directory.objects.create(name=f"Root", owner=request.user, parent=None)
        except Directory.MultipleObjectsReturned:
            # 如果意外有多个根目录，取第一个
            root_dir = Directory.objects.filter(owner=request.user, parent__isnull=True).first()

        # 获取根目录下的内容
        subdirs = Directory.objects.filter(parent=root_dir)
        dir_serializer = DirectorySerializer(subdirs, many=True)

        files = File.objects.filter(directory=root_dir)
        file_serializer = FileSerializer(files, many=True)

        return Response({
            'directory': dir_serializer.data,
            'files': file_serializer.data,
            'id': root_dir.id,
            'root_name': '/  ' + root_dir.name
        })

    def destroy(self, request, *args, **kwargs):
        directory = self.get_object()

        # 递归删除所有MinIO文件
        self.delete_directory_files(directory)

        # 级联删除数据库记录（自动处理子目录和文件）
        directory.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete_directory_files(self, directory):
        """递归删除目录下所有文件"""
        minio_client = get_minio_client()
        for file in directory.files.all():
            storage_name = file.storage_name
            # 检查是否有其他文件引用相同的MinIO文件
            other_references = File.objects.filter(
                storage_name=storage_name
            ).exclude(id=file.id).exists()

            if not other_references:
                try:
                    minio_client.remove_object(
                        settings.MINIO_CONFIG['BUCKET_NAME'],
                        storage_name
                    )
                except S3Error as e:
                    if e.code != "NoSuchKey":  # 忽略文件不存在的错误
                        # 记录错误但继续删除
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"MinIO删除错误: {str(e)}")

        # 递归处理子目录
        for child in directory.children.all():
            self.delete_directory_files(child)


class FileViewSet(ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [IsOwnerOrAdminReadWriteOnly]
    filter_backends = [CurrentUserFilterBackend]
    authentication_classes = [JWTAuthentication]

    def create(self, request):
        minio_client = get_minio_client()
        directory_id = request.data.get('directory')
        directory = get_object_or_404(Directory, id=directory_id)
        uploaded_file = request.FILES['file']
        file_hash = generate_file_hash(uploaded_file)
        file_extension = os.path.splitext(uploaded_file.name)[1]
        storage_name = f"{file_hash}{file_extension}"

        try:
            # 上传到 MinIO
            minio_client.put_object(
                settings.MINIO_CONFIG['BUCKET_NAME'],
                storage_name,
                uploaded_file,
                length=uploaded_file.size,
                content_type=uploaded_file.content_type
            )

            # 保存到数据库
            file_obj = File.objects.create(
                name=uploaded_file.name,
                directory=directory,
                storage_name=storage_name,
                size=uploaded_file.size,
                owner=request.user,
                content_type=uploaded_file.content_type
            )

            return Response(FileSerializer(file_obj).data, status=status.HTTP_201_CREATED)

        except S3Error as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        minio_client = get_minio_client()
        file_obj = self.get_object()

        try:
            # 从 MinIO 获取文件
            response = minio_client.get_object(
                settings.MINIO_CONFIG['BUCKET_NAME'],
                file_obj.storage_name
            )
            from urllib.parse import quote

            safe_name = quote(file_obj.name)
            content_disposition = f"attachment; filename*=UTF-8''{safe_name}"

            # 创建 Django 文件响应
            from django.http import HttpResponse
            res = HttpResponse(response.data)
            res['Content-Type'] = file_obj.content_type
            res['Content-Disposition'] = content_disposition
            res['Access-Control-Expose-Headers'] = 'Content-Disposition'
            return res

        except S3Error as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        finally:
            response.close()
            response.release_conn()

    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({"error": "缺少搜索参数"}, status=status.HTTP_400_BAD_REQUEST)

        # 搜索当前用户的所有文件（全局）
        files = File.objects.filter(
            owner=request.user,
            name__icontains=query
        ).select_related('directory').order_by('-uploaded_at')

        # 搜索当前用户的所有目录（全局）
        directories = Directory.objects.filter(
            owner=request.user,
            name__icontains=query
        ).order_by('-created_at')

        file_serializer = FileSerializer(files, many=True)
        dir_serializer = DirectorySerializer(directories, many=True)

        return Response({
            'files': file_serializer.data,
            'directories': dir_serializer.data
        })

    def destroy(self, request, *args, **kwargs):
        minio_client = get_minio_client()
        file_obj = self.get_object()
        storage_name = file_obj.storage_name

        # 检查是否有其他文件引用相同的MinIO文件
        other_references = File.objects.filter(
            storage_name=storage_name
        ).exclude(id=file_obj.id).exists()

        # 只有当没有其他引用时才删除MinIO文件
        if not other_references:
            try:
                minio_client.remove_object(
                    settings.MINIO_CONFIG['BUCKET_NAME'],
                    storage_name
                )
            except S3Error as e:
                # 文件不存在时忽略错误
                if e.code != "NoSuchKey":
                    return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 删除数据库记录
        file_obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
