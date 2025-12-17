"""
本地文件系统存储后端
用于测试环境的简单存储实现
"""

import os
import shutil
from typing import Optional, BinaryIO, Dict, Any
from django.conf import settings
from .storage_factory import StorageBackend
import logging

logger = logging.getLogger(__name__)


class LocalStorageBackend(StorageBackend):
    """本地文件系统存储后端"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # 使用项目根目录下的 uploads 文件夹
        self.base_path = config.get('BASE_PATH', os.path.join(settings.BASE_DIR, 'uploads'))
        self.ensure_directory_exists()

    def ensure_directory_exists(self):
        """确保存储目录存在"""
        os.makedirs(self.base_path, exist_ok=True)

    def upload_file(self, object_name: str, file_data: BinaryIO, 
                   content_type: str = None, metadata: Dict[str, str] = None) -> bool:
        """上传文件到本地文件系统"""
        try:
            file_path = os.path.join(self.base_path, object_name)

            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 写入文件
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file_data, f)

            logger.info(f"文件上传成功: {object_name}")
            return True

        except Exception as e:
            logger.error(f"文件上传失败: {object_name}, 错误: {str(e)}")
            return False

    def download_file(self, object_name: str) -> Optional[BinaryIO]:
        """从本地文件系统下载文件"""
        try:
            file_path = os.path.join(self.base_path, object_name)

            if not os.path.exists(file_path):
                logger.warning(f"文件不存在: {object_name}")
                return None

            return open(file_path, 'rb')

        except Exception as e:
            logger.error(f"文件下载失败: {object_name}, 错误: {str(e)}")
            return None

    def delete_file(self, object_name: str) -> bool:
        """删除本地文件系统中的文件"""
        try:
            file_path = os.path.join(self.base_path, object_name)

            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"文件删除成功: {object_name}")
                return True
            else:
                logger.warning(f"文件不存在，无法删除: {object_name}")
                return False

        except Exception as e:
            logger.error(f"文件删除失败: {object_name}, 错误: {str(e)}")
            return False

    def file_exists(self, object_name: str) -> bool:
        """检查本地文件系统中的文件是否存在"""
        file_path = os.path.join(self.base_path, object_name)
        return os.path.exists(file_path)

    def get_file_url(self, object_name: str, expires: int = 3600) -> str:
        """获取文件访问URL（本地文件系统返回文件路径）"""
        file_path = os.path.join(self.base_path, object_name)

        if os.path.exists(file_path):
            # 返回绝对路径
            return os.path.abspath(file_path)
        else:
            logger.warning(f"文件不存在: {object_name}")
            return ""
