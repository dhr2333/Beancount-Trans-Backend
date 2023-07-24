from rest_framework.generics import CreateAPIView

from .serializers import CreateUserSerializer


class UserView(CreateAPIView):
    """用户注册"""
    serializer_class = CreateUserSerializer
