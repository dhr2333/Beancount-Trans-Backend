from abc import ABC, abstractmethod
from typing import Optional, BinaryIO, Dict, Any
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """存储后端抽象基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bucket_name = config.get('BUCKET_NAME', 'beancount-trans')

    @abstractmethod
    def upload_file(self, object_name: str, file_data: BinaryIO, 
                   content_type: str = None, metadata: Dict[str, str] = None) -> bool:
        """上传文件"""
        pass

    @abstractmethod
    def download_file(self, object_name: str) -> Optional[BinaryIO]:
        """下载文件"""
        pass

    @abstractmethod
    def delete_file(self, object_name: str) -> bool:
        """删除文件"""
        pass

    @abstractmethod
    def file_exists(self, object_name: str) -> bool:
        """检查文件是否存在"""
        pass

    @abstractmethod
    def get_file_url(self, object_name: str, expires: int = 3600) -> str:
        """获取文件访问URL"""
        pass


class StorageFactory:
    """存储工厂类"""

    _instance = None
    _backend = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_backend(self) -> StorageBackend:
        """获取存储后端实例"""
        if self._backend is None:
            storage_type = getattr(settings, 'STORAGE_TYPE', 'minio')

            if storage_type == 'minio':
                from .minio import MinIOBackend
                config = getattr(settings, 'MINIO_CONFIG', {})
                self._backend = MinIOBackend(config)
            elif storage_type == 'oss':
                from .oss_conn import OSSBackend
                config = getattr(settings, 'OSS_CONFIG', {})
                self._backend = OSSBackend(config)
            elif storage_type == 's3':
                from .s3_conn import S3Backend
                config = getattr(settings, 'S3_CONFIG', {})
                self._backend = S3Backend(config)
            elif storage_type == 'local':
                from .local_storage import LocalStorageBackend
                config = getattr(settings, 'LOCAL_STORAGE_CONFIG', {})
                self._backend = LocalStorageBackend(config)
            else:
                raise ValueError(f"不支持的存储类型: {storage_type}")

        return self._backend


# 全局存储实例
def get_storage_client() -> StorageBackend:
    """获取存储客户端实例"""
    return StorageFactory().get_backend()
