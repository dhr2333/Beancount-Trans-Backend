from django.contrib.auth import authenticate
from django.contrib.auth.models import Group
from rest_framework import permissions
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers import CreateUserSerializer, UserSerializer, GroupSerializer


class LoginView(TokenObtainPairView):
    serializer_class = TokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        # 获取用户输入的信息
        username_or_phone_number = request.data.get('username')
        password = request.data.get('password')

        # 判断是用户名还是手机号
        if username_or_phone_number.isdigit():  # 手机号
            # 使用数据库查询验证手机号是否存在
            user = User.objects.filter(mobile=username_or_phone_number).first()
        else:  # 用户名
            # 使用用户名查找用户
            user = User.objects.filter(username=username_or_phone_number).first()

        if user is not None:
            # 使用authenticate方法验证用户的密码
            authenticated_user = authenticate(username=user.username, password=password)
            if authenticated_user:
                # 登录成功，生成JWT令牌并返回给前端
                serializer = TokenObtainPairSerializer(data={'username': user.username, 'password': password})
                serializer.is_valid(raise_exception=True)
                access = serializer.validated_data.get('access')
                refresh = serializer.validated_data.get('refresh')
                # token, _ = Token.objects.get_or_create(user=user)
                response_data = {
                    'access': str(access),
                    'refresh': str(refresh),
                    # 'token': token.key,
                }
                return Response(response_data)

        # 登录失败，返回错误信息
        return Response({'detail': 'Invalid credentials'}, status=400)


class CreateUserView(CreateAPIView):
    """用户注册"""
    serializer_class = CreateUserSerializer


class UserViewSet(ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    # queryset = User.objects.all().order_by('-date_joined')
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]
