from minio import Minio
from minio.error import S3Error
from django.conf import settings
import logging
import uuid

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
        return cls._instance

    def upload_file(self, bucket_name, file_obj, file_name):
        """上传文件到MinIO"""
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)

        object_name = f"{uuid.uuid4().hex}_{file_name}"
        
        try:
            self.client.put_object(
                bucket_name,
                object_name,
                file_obj,
                length=file_obj.size
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
