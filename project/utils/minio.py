from minio import Minio
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from minio.error import S3Error

_minio_client = None

def get_minio_client():
    global _minio_client
    if _minio_client is None:
        try:
            config = settings.MINIO_CONFIG
            _minio_client = Minio(
                config['ENDPOINT'],
                access_key=config['ACCESS_KEY'],
                secret_key=config['SECRET_KEY'],
                secure=config['USE_HTTPS']
            )
            # 测试连接是否有效
            _minio_client.list_buckets()
        except AttributeError:
            raise ImproperlyConfigured("MINIO_CONFIG is missing in settings")
        except S3Error as e:
            if e.code == "InvalidAccessKeyId":
                raise ImproperlyConfigured("MinIO access key is invalid")
            raise
    return _minio_client
