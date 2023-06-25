from django.db import DatabaseError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """⾃定义异常
    补充捕获DRF以外的异常信息
    """
    response = exception_handler(exc, context)
    print(exc)  # exc 引发异常的异常对象
    view = context['view']  # context 异常发生的上下文
    if response is None:
        if isinstance(exc, DatabaseError):
            print('[%s]: %s' % (view, exc))
            response = Response({'detail': '服务器内部错误'}, status=status.HTTP_507_INSUFFICIENT_STORAGE)
    return response
