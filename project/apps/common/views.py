from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from project.apps.common.permissions import IsOwnerOrAdminReadWriteOnly, AnonymousReadOnlyPermission
from project.apps.common.filters import CurrentUserFilterBackend, AnonymousUserFilterBackend


class BaseMappingViewSet(ModelViewSet):
    """
    映射视图集基类，提供通用的映射管理功能
    支持匿名用户访问id=1用户的数据（只读）
    """
    permission_classes = [AnonymousReadOnlyPermission]
    filter_backends = [AnonymousUserFilterBackend]
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        """重写create方法，实现批量创建"""
        if self.request.user.is_anonymous:
            raise PermissionDenied("Permission denied. Please log in.")

        serializer = self.get_serializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)

        if isinstance(request.data, list):
            # 如果是列表，则删除原有数据，保存新数据
            self.get_queryset().filter(owner_id=self.request.user).delete()
            serializer.save(owner=self.request.user)
            return Response(serializer.data)
        else:
            return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """创建时设置属主并检查重复"""
        if self.request.user.is_anonymous:
            raise PermissionDenied("Permission denied. Please log in.")

        # 检查key是否已存在
        key = self.request.data.get("key")
        if key and self.get_queryset().filter(owner_id=self.request.user, key=key).exists():
            raise ValidationError("Account already exists.")

        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        """更新时检查重复"""
        instance = self.get_object()
        key = self.request.data.get('key', instance.key)

        if key and self.get_queryset().filter(owner_id=self.request.user, key=key).exclude(id=instance.id).exists():
            raise ValidationError("Account already exists.")

        serializer.save(owner=self.request.user)
