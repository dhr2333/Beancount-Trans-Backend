# project/apps/file_manager/views.py
import os
# from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
# from minio.error import S3Error
from project.apps.file_manager.models import Directory, File
from project.apps.translate.models import ParseFile
from project.apps.file_manager.serializers import DirectorySerializer, FileSerializer
from project.apps.common.filters import CurrentUserFilterBackend
from project.apps.common.permissions import IsOwnerOrAdminReadWriteOnly
from project.utils.file import generate_file_hash
from project.utils.storage_factory import get_storage_client
from project.utils.file import BeanFileManager


class DirectoryViewSet(ModelViewSet):
    """
    目录管理视图集

    提供目录的增删改查功能，包括获取目录内容等操作。
    所有操作都需要用户认证，且只能操作自己的数据。
    """
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

        # 递归删除所有.bean文件并更新main.bean
        self._delete_bean_files_for_directory(request.user, directory)

        # 递归删除所有MinIO文件
        self._delete_directory_files(directory)

        # 级联删除数据库记录（自动处理子目录和文件）
        directory.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def _delete_directory_files(self, directory):
        """递归删除目录下所有文件"""
        storage_client = get_storage_client()
        for file in directory.files.all():
            storage_name = file.storage_name
            # 检查是否有其他文件引用相同的存储文件
            other_references = File.objects.filter(
                storage_name=storage_name
            ).exclude(id=file.id).exists()

            if not other_references:
                try:
                    storage_client.delete_file(storage_name)
                except Exception as e:
                    # 记录错误但继续删除
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"存储删除错误: {str(e)}")

        # 递归处理子目录
        for child in directory.children.all():
            self._delete_directory_files(child)

    def _delete_bean_files_for_directory(self, user, directory):
        """递归删除目录下所有文件对应的.bean文件并更新trans/main.bean"""
        # 处理当前目录下的文件
        for file in directory.files.all():
            base_name = os.path.splitext(file.name)[0]
            bean_filename = f"{base_name}.bean"

            # 从trans/main.bean中移除include语句
            BeanFileManager.update_trans_main_bean_include(
                user,
                bean_filename,
                action='remove'
            )

            # 删除.bean文件（从trans目录）
            BeanFileManager.delete_bean_file(user, bean_filename)

        # 递归处理子目录
        for child in directory.children.all():
            self._delete_bean_files_for_directory(user, child)


class FileViewSet(ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [IsOwnerOrAdminReadWriteOnly]
    filter_backends = [CurrentUserFilterBackend]
    authentication_classes = [JWTAuthentication]

    def create(self, request):
        storage_client = get_storage_client()
        directory_id = request.data.get('directory')
        directory = get_object_or_404(Directory, id=directory_id)
        uploaded_file = request.FILES['file']
        
        # 检测是否存在同名文件（排除当前目录）
        existing_files = File.objects.filter(
            owner=request.user,
            name=uploaded_file.name
        ).exclude(directory=directory).select_related('directory')
        
        if existing_files.exists():
            # 构建已存在文件的目录路径信息
            existing_files_info = [
                {
                    'directory_path': file.directory.get_path(),
                    'directory_id': file.directory.id
                }
                for file in existing_files
            ]
            return Response({
                "error": "存在同名文件，为避免解析结果冲突，请重命名文件",
                "existing_files": existing_files_info
            }, status=status.HTTP_400_BAD_REQUEST)
        
        file_hash = generate_file_hash(uploaded_file)
        file_extension = os.path.splitext(uploaded_file.name)[1]
        storage_name = f"{file_hash}{file_extension}"

        try:
            # 上传到存储
            success = storage_client.upload_file(
                storage_name,
                uploaded_file,
                content_type=uploaded_file.content_type
            )

            if not success:
                return Response({"error": "文件上传失败"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 保存到数据库
            file_obj = File.objects.create(
                name=uploaded_file.name,
                directory=directory,
                storage_name=storage_name,
                size=uploaded_file.size,
                owner=request.user,
                content_type=uploaded_file.content_type
            )

            ParseFile.objects.create(
               file=file_obj,
            )

            bean_filename = BeanFileManager.create_bean_file(
                request.user,
                uploaded_file.name
            )
            # 上传文件时即向trans/main.bean增加对应文件的include
            BeanFileManager.update_trans_main_bean_include(
                request.user,
                bean_filename,
                action='add'
            )

            return Response(FileSerializer(file_obj).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        storage_client = get_storage_client()
        file_obj = self.get_object()

        try:
            # 从存储获取文件
            file_data = storage_client.download_file(file_obj.storage_name)

            if file_data is None:
                return Response({"error": "文件不存在"}, status=status.HTTP_404_NOT_FOUND)

            from urllib.parse import quote
            safe_name = quote(file_obj.name)
            content_disposition = f"attachment; filename*=UTF-8''{safe_name}"

            # 创建 Django 文件响应
            from django.http import HttpResponse
            res = HttpResponse(file_data.getvalue())
            res['Content-Type'] = file_obj.content_type
            res['Content-Disposition'] = content_disposition
            res['Access-Control-Expose-Headers'] = 'Content-Disposition'
            return res

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

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
        storage_client = get_storage_client()
        file_obj = self.get_object()
        storage_name = file_obj.storage_name

        # ParseFile.objects.filter(file=file_obj).delete()

        base_name = os.path.splitext(file_obj.name)[0]
        bean_filename = f"{base_name}.bean"

        # 从trans/main.bean中移除include语句
        BeanFileManager.update_trans_main_bean_include(
            request.user,
            bean_filename,
            action='remove'
        )

        # 删除.bean文件（从trans目录）
        BeanFileManager.delete_bean_file(
            request.user,
            bean_filename
        )

        # 检查是否有其他文件引用相同的存储文件
        other_references = File.objects.filter(
            storage_name=storage_name
        ).exclude(id=file_obj.id).exists()

        # 只有当没有其他引用时才删除存储文件
        if not other_references:
            try:
                storage_client.delete_file(storage_name)
            except Exception as e:
                # 记录错误但不中断删除流程
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"存储文件删除失败: {str(e)}")

        # 删除数据库记录
        file_obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
