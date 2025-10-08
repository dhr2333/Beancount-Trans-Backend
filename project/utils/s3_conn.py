import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from .storage_factory import StorageBackend
from typing import Optional, BinaryIO, Dict
import logging
from io import BytesIO

logger = logging.getLogger(__name__)


class S3Backend(StorageBackend):
    """通用S3存储后端实现（支持MinIO和阿里云OSS）"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self._client = None
        self._resource = None

    def _get_client(self):
        """获取S3客户端"""
        if self._client is None:
            try:
                # 创建S3客户端
                self._client = boto3.client(
                    's3',
                    endpoint_url=self.config.get('ENDPOINT_URL'),
                    aws_access_key_id=self.config['ACCESS_KEY_ID'],
                    aws_secret_access_key=self.config['SECRET_ACCESS_KEY'],
                    region_name=self.config.get('REGION', 'us-east-1'),
                    use_ssl=self.config.get('USE_SSL', True),
                    verify=self.config.get('VERIFY_SSL', True)
                )

                # 测试连接
                self._client.head_bucket(Bucket=self.bucket_name)

            except KeyError as e:
                raise ImproperlyConfigured(f"S3配置缺失: {e}")
            except NoCredentialsError:
                raise ImproperlyConfigured("S3凭证配置错误")
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'NoSuchBucket':
                    # 尝试创建Bucket
                    try:
                        self._client.create_bucket(Bucket=self.bucket_name)
                        # logger.info(f"创建S3 Bucket: {self.bucket_name}")
                    except Exception as create_error:
                        raise ImproperlyConfigured(f"无法创建S3 Bucket: {str(create_error)}")
                else:
                    raise ImproperlyConfigured(f"S3连接失败: {str(e)}")
            except Exception as e:
                raise ImproperlyConfigured(f"S3连接失败: {str(e)}")

        return self._client

    def upload_file(self, object_name: str, file_data: BinaryIO, 
                   content_type: str = None, metadata: Dict[str, str] = None) -> bool:
        """上传文件到S3"""
        try:
            client = self._get_client()

            # 准备上传参数
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            if metadata:
                extra_args['Metadata'] = metadata

            # 上传文件
            client.upload_fileobj(file_data, self.bucket_name, object_name, ExtraArgs=extra_args)
            # logger.info(f"S3文件上传成功: {object_name}")
            return True

        except Exception as e:
            logger.error(f"S3上传文件失败: {object_name}, 错误: {str(e)}")
            return False

    def download_file(self, object_name: str) -> Optional[BinaryIO]:
        """从S3下载文件"""
        try:
            client = self._get_client()

            # 下载文件
            response = client.get_object(Bucket=self.bucket_name, Key=object_name)

            # 读取文件内容到内存
            file_data = BytesIO(response['Body'].read())
            file_data.seek(0)

            return file_data

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning(f"S3文件不存在: {object_name}")
            else:
                logger.error(f"S3下载文件失败: {object_name}, 错误: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"S3下载文件失败: {object_name}, 错误: {str(e)}")
            return None

    def delete_file(self, object_name: str) -> bool:
        """从S3删除文件"""
        try:
            client = self._get_client()
            client.delete_object(Bucket=self.bucket_name, Key=object_name)
            # logger.info(f"S3文件删除成功: {object_name}")
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                # 文件不存在，视为删除成功
                logger.info(f"S3文件不存在，视为删除成功: {object_name}")
                return True
            else:
                logger.error(f"S3删除文件失败: {object_name}, 错误: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"S3删除文件失败: {object_name}, 错误: {str(e)}")
            return False

    def file_exists(self, object_name: str) -> bool:
        """检查文件是否存在于S3"""
        try:
            client = self._get_client()
            client.head_object(Bucket=self.bucket_name, Key=object_name)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                return False
            else:
                logger.error(f"S3检查文件存在失败: {object_name}, 错误: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"S3检查文件存在失败: {object_name}, 错误: {str(e)}")
            return False

    def get_file_url(self, object_name: str, expires: int = 3600) -> str:
        """获取S3文件访问URL"""
        try:
            client = self._get_client()
            url = client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_name},
                ExpiresIn=expires
            )
            return url
        except Exception as e:
            logger.error(f"S3获取文件URL失败: {object_name}, 错误: {str(e)}")
            return ""


def get_s3_client():
    """获取S3客户端（向后兼容）"""
    storage_type = getattr(settings, 'STORAGE_TYPE', 'minio')

    if storage_type == 'minio':
        config = getattr(settings, 'MINIO_CONFIG', {})
        s3_config = {
            'ENDPOINT_URL': f"http{'s' if config.get('USE_HTTPS') else ''}://{config['ENDPOINT']}",
            'ACCESS_KEY_ID': config['ACCESS_KEY'],
            'SECRET_ACCESS_KEY': config['SECRET_KEY'],
            'BUCKET_NAME': config['BUCKET_NAME'],
            'USE_SSL': config.get('USE_HTTPS', False),
            'VERIFY_SSL': False  # MinIO通常不需要SSL验证
        }
    elif storage_type == 'oss':
        config = getattr(settings, 'OSS_CONFIG', {})
        s3_config = {
            'ENDPOINT_URL': config['ENDPOINT'],
            'ACCESS_KEY_ID': config['ACCESS_KEY_ID'],
            'SECRET_ACCESS_KEY': config['ACCESS_KEY_SECRET'],
            'BUCKET_NAME': config['BUCKET_NAME'],
            'REGION': config.get('REGION', 'cn-hangzhou'),
            'USE_SSL': True,
            'VERIFY_SSL': True
        }
    else:
        raise ValueError(f"不支持的存储类型: {storage_type}")

    backend = S3Backend(s3_config)
    return backend._get_client()
