import oss2
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from .storage_factory import StorageBackend
from typing import Optional, BinaryIO, Dict
import logging
from io import BytesIO

logger = logging.getLogger(__name__)


class OSSBackend(StorageBackend):
    """阿里云OSS存储后端实现"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self._client = None
        self._bucket = None
    
    def _get_client(self):
        """获取OSS客户端"""
        if self._client is None:
            try:
                # 创建Auth对象
                auth = oss2.Auth(
                    self.config['ACCESS_KEY_ID'],
                    self.config['ACCESS_KEY_SECRET']
                )
                
                # 创建Bucket对象
                endpoint = self.config['ENDPOINT']
                self._bucket = oss2.Bucket(auth, endpoint, self.bucket_name)
                
                # 测试连接
                self._bucket.get_bucket_info()
                
            except KeyError as e:
                raise ImproperlyConfigured(f"OSS配置缺失: {e}")
            except Exception as e:
                raise ImproperlyConfigured(f"OSS连接失败: {str(e)}")
        
        return self._bucket
    
    def upload_file(self, object_name: str, file_data: BinaryIO, 
                   content_type: str = None, metadata: Dict[str, str] = None) -> bool:
        """上传文件到OSS"""
        try:
            bucket = self._get_client()
            
            # 准备元数据
            headers = {}
            if content_type:
                headers['Content-Type'] = content_type
            if metadata:
                for key, value in metadata.items():
                    headers[f'x-oss-meta-{key}'] = value
            
            # 获取文件大小
            file_data.seek(0, 2)  # 移动到文件末尾
            file_size = file_data.tell()
            file_data.seek(0)  # 重置到文件开头
            
            # 上传文件
            result = bucket.put_object(object_name, file_data, headers=headers)
            
            if result.status == 200:
                # logger.info(f"OSS文件上传成功: {object_name}")
                return True
            else:
                logger.error(f"OSS文件上传失败: {object_name}, 状态码: {result.status}")
                return False
                
        except Exception as e:
            logger.error(f"OSS上传文件失败: {object_name}, 错误: {str(e)}")
            return False
    
    def download_file(self, object_name: str) -> Optional[BinaryIO]:
        """从OSS下载文件"""
        try:
            bucket = self._get_client()
            
            # 下载文件
            result = bucket.get_object(object_name)
            
            # 读取文件内容到内存
            file_data = BytesIO(result.read())
            file_data.seek(0)
            
            return file_data
            
        except oss2.exceptions.NoSuchKey:
            logger.warning(f"OSS文件不存在: {object_name}")
            return None
        except Exception as e:
            logger.error(f"OSS下载文件失败: {object_name}, 错误: {str(e)}")
            return None
    
    def delete_file(self, object_name: str) -> bool:
        """从OSS删除文件"""
        try:
            bucket = self._get_client()
            result = bucket.delete_object(object_name)
            
            if result.status == 204:  # 删除成功
                # logger.info(f"OSS文件删除成功: {object_name}")
                return True
            else:
                logger.error(f"OSS文件删除失败: {object_name}, 状态码: {result.status}")
                return False
                
        except oss2.exceptions.NoSuchKey:
            # 文件不存在，视为删除成功
            logger.info(f"OSS文件不存在，视为删除成功: {object_name}")
            return True
        except Exception as e:
            logger.error(f"OSS删除文件失败: {object_name}, 错误: {str(e)}")
            return False
    
    def file_exists(self, object_name: str) -> bool:
        """检查文件是否存在于OSS"""
        try:
            bucket = self._get_client()
            bucket.head_object(object_name)
            return True
        except oss2.exceptions.NoSuchKey:
            return False
        except Exception as e:
            logger.error(f"OSS检查文件存在失败: {object_name}, 错误: {str(e)}")
            return False
    
    def get_file_url(self, object_name: str, expires: int = 3600) -> str:
        """获取OSS文件访问URL"""
        try:
            bucket = self._get_client()
            url = bucket.sign_url('GET', object_name, expires)
            return url
        except Exception as e:
            logger.error(f"OSS获取文件URL失败: {object_name}, 错误: {str(e)}")
            return ""
    
    def get_bucket_url(self) -> str:
        """获取OSS Bucket的基础URL"""
        try:
            endpoint = self.config['ENDPOINT']
            if endpoint.startswith('http'):
                return f"{endpoint}/{self.bucket_name}"
            else:
                return f"https://{endpoint}/{self.bucket_name}"
        except Exception as e:
            logger.error(f"OSS获取Bucket URL失败: {str(e)}")
            return ""
