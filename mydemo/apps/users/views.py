from django.contrib.auth.models import Group
from rest_framework import permissions
from rest_framework.generics import CreateAPIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import User
from .serializers import CreateUserSerializer, UserSerializer, GroupSerializer


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
