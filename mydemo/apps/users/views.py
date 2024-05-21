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
        username_or_phone_number = request.data.get('username')
        password = request.data.get('password')

        if username_or_phone_number.isdigit():
            user = User.objects.filter(mobile=username_or_phone_number).first()
        else:
            user = User.objects.filter(username=username_or_phone_number).first()

        if user is not None:
            authenticated_user = authenticate(username=user.username, password=password)
            if authenticated_user:
                serializer = TokenObtainPairSerializer(data={'username': user.username, 'password': password})
                serializer.is_valid(raise_exception=True)
                access = serializer.validated_data.get('access')
                refresh = serializer.validated_data.get('refresh')
                response_data = {
                    'access': str(access),
                    'refresh': str(refresh),
                }
                return Response(response_data)

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
