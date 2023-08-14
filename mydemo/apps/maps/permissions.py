from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet.
        return obj.owner == request.user


class IsOwnerOrAdminReadWriteOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # 允许管理员对所有对象进行读写
        if request.user.is_superuser:
            return True

        # 允许属主对其对象进行读写
        if obj.owner == request.user:
            return True

        # 其他用户没有读写权限
        return False

class IsOwner(permissions.BasePermission):
       def has_object_permission(self, request, view, obj):
           # 检查对象的创建者是否与请求的用户相同
           return obj.created_by == request.user