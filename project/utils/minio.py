from minio import Minio
from django.conf import settings


minio_client = Minio(
    settings.MINIO_CONFIG['ENDPOINT'],
    access_key=settings.MINIO_CONFIG['ACCESS_KEY'],
    secret_key=settings.MINIO_CONFIG['SECRET_KEY'],
    secure=settings.MINIO_CONFIG['USE_HTTPS']
)