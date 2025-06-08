from minio import Minio
from minio.error import S3Error
from django.conf import settings
import logging
import uuid
import mimetypes
from io import BytesIO

logger = logging.getLogger(__name__)

class MinIOClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_USE_SSL
            )
            # 确保存储桶存在
            if not cls._instance.client.bucket_exists(settings.MINIO_BUCKET_NAME):
                cls._instance.client.make_bucket(settings.MINIO_BUCKET_NAME)
        return cls._instance

    def upload_file(self, bucket_name, file_obj, file_name):
        """上传文件到MinIO"""
        try:
            # 生成唯一的对象名称
            object_name = f"{uuid.uuid4().hex}/{file_name}"
            
            # 获取文件的MIME类型
            mime_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'
            
            # 上传文件
            self.client.put_object(
                bucket_name,
                object_name,
                file_obj,
                length=file_obj.size,
                content_type=mime_type
            )
            return object_name
        except S3Error as e:
            logger.error(f"MinIO upload failed: {e}")
            raise

    def get_file(self, bucket_name, object_name):
        """从MinIO获取文件"""
        try:
            response = self.client.get_object(bucket_name, object_name)
            return response
        except S3Error as e:
            logger.error(f"MinIO download failed: {e}")
            raise FileNotFoundError(f"File not found in MinIO: {e}")

    def delete_file(self, bucket_name, object_name):
        """从MinIO删除文件"""
        try:
            self.client.remove_object(bucket_name, object_name)
        except S3Error as e:
            logger.error(f"MinIO delete failed: {e}")
            raise

    def get_file_url(self, bucket_name, object_name, expires=3600):
        """获取文件的临时访问URL"""
        try:
            return self.client.presigned_get_object(
                bucket_name,
                object_name,
                expires=expires
            )
        except S3Error as e:
            logger.error(f"MinIO get URL failed: {e}")
            raise

    def copy_file(self, bucket_name, source_object, dest_object):
        """复制MinIO中的文件"""
        try:
            self.client.copy_object(
                bucket_name,
                dest_object,
                f"{bucket_name}/{source_object}"
            )
        except S3Error as e:
            logger.error(f"MinIO copy failed: {e}")
            raise
