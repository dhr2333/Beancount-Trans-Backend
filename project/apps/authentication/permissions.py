from rest_framework import permissions
from project.apps.authentication.models import UserProfile


class PhoneNumberVerifiedPermission(permissions.BasePermission):
    """
    手机号验证权限类
    要求用户必须已验证手机号才能访问
    """

    def has_permission(self, request, view):
        """检查是否有权限访问视图"""
        # 需要用户认证
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            profile = request.user.profile
            return profile.is_phone_verified()
        except UserProfile.DoesNotExist:
            # 如果profile不存在，创建它
            UserProfile.objects.create(user=request.user)
            return False
        except Exception:
            return False


class PhoneNumberOrReadOnlyPermission(permissions.BasePermission):
    """
    手机号验证权限类（只读操作除外）
    允许读取操作，但写入操作需要验证手机号
    """

    def has_permission(self, request, view):
        """检查是否有权限访问视图"""
        # 允许只读操作
        if request.method in permissions.SAFE_METHODS:
            return True

        # 需要用户认证
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            profile = request.user.profile
            return profile.is_phone_verified()
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=request.user)
            return False
        except Exception:
            return False

