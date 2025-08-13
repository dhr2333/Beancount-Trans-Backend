from minio import Minio
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from minio.error import S3Error
from .storage_factory import StorageBackend
from typing import Optional, BinaryIO, Dict
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

_minio_client = None


class MinIOBackend(StorageBackend):
    """MinIO存储后端实现"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self._client = None
    
    def _get_client(self):
        """获取MinIO客户端"""
        global _minio_client
        if _minio_client is None:
            try:
                _minio_client = Minio(
                    self.config['ENDPOINT'],
                    access_key=self.config['ACCESS_KEY'],
                    secret_key=self.config['SECRET_KEY'],
                    secure=self.config.get('USE_HTTPS', False)
                )
                # 测试连接是否有效
                _minio_client.list_buckets()
            except AttributeError:
                raise ImproperlyConfigured("MINIO_CONFIG配置缺失")
            except S3Error as e:
                if e.code == "InvalidAccessKeyId":
                    raise ImproperlyConfigured("MinIO访问密钥无效")
                raise
        return _minio_client
    
    def upload_file(self, object_name: str, file_data: BinaryIO, 
                   content_type: str = None, metadata: Dict[str, str] = None) -> bool:
        """上传文件到MinIO"""
        try:
            client = self._get_client()
            
            # 获取文件大小
            file_data.seek(0, 2)  # 移动到文件末尾
            file_size = file_data.tell()
            file_data.seek(0)  # 重置到文件开头
            
            client.put_object(
                self.bucket_name,
                object_name,
                file_data,
                length=file_size,
                content_type=content_type,
                metadata=metadata
            )
            return True
        except Exception as e:
            logger.error(f"MinIO上传文件失败: {object_name}, 错误: {str(e)}")
            return False
    
    def download_file(self, object_name: str) -> Optional[BinaryIO]:
        """从MinIO下载文件"""
        try:
            client = self._get_client()
            response = client.get_object(self.bucket_name, object_name)
            
            # 读取文件内容到内存
            file_data = BytesIO(response.read())
            response.close()
            response.release_conn()
            
            file_data.seek(0)
            return file_data
        except Exception as e:
            logger.error(f"MinIO下载文件失败: {object_name}, 错误: {str(e)}")
            return None
    
    def delete_file(self, object_name: str) -> bool:
        """从MinIO删除文件"""
        try:
            client = self._get_client()
            client.remove_object(self.bucket_name, object_name)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                # 文件不存在，视为删除成功
                return True
            logger.error(f"MinIO删除文件失败: {object_name}, 错误: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"MinIO删除文件失败: {object_name}, 错误: {str(e)}")
            return False
    
    def file_exists(self, object_name: str) -> bool:
        """检查文件是否存在于MinIO"""
        try:
            client = self._get_client()
            client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            logger.error(f"MinIO检查文件存在失败: {object_name}, 错误: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"MinIO检查文件存在失败: {object_name}, 错误: {str(e)}")
            return False
    
    def get_file_url(self, object_name: str, expires: int = 3600) -> str:
        """获取MinIO文件访问URL"""
        try:
            client = self._get_client()
            return client.presigned_get_object(self.bucket_name, object_name, expires=expires)
        except Exception as e:
            logger.error(f"MinIO获取文件URL失败: {object_name}, 错误: {str(e)}")
            return ""


# 保持向后兼容的函数
def get_minio_client():
    """获取MinIO客户端（向后兼容）"""
    backend = MinIOBackend(settings.MINIO_CONFIG)
    return backend._get_client()
