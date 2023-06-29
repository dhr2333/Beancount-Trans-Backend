import logging

from django.db import DatabaseError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """⾃定义异常
    补充捕获DRF以外的异常信息
    """
    response = exception_handler(exc, context)  # 调用drf框架原生的异常处理方法

    if response is None:
        view = context['view']  # exc 异常实例对象 context 异常发生的上下文
        if isinstance(exc, DatabaseError):
            logging.error('[%s] %s' % (view, exc))
            response = Response({'message': '服务器内部错误'}, status=status.HTTP_507_INSUFFICIENT_STORAGE)
    return response
