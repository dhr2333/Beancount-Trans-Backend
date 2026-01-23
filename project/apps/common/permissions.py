from rest_framework import permissions


class IsOwnerOrAdminReadWriteOnly(permissions.BasePermission):
    """
    统一权限类：只允许用户操作自己的数据，或管理员有完全权限
    """

    def has_permission(self, request, view):
        """检查是否有权限访问视图"""
        # 需要用户认证
        if not request.user or not request.user.is_authenticated:
            return False

        # 管理员有完全权限
        if request.user.is_staff or request.user.is_superuser:
            return True

        # 普通用户只能访问自己的数据
        return True

    def has_object_permission(self, request, view, obj):
        """检查是否有权限操作特定对象"""
        # 管理员有完全权限
        if request.user.is_staff or request.user.is_superuser:
            return True

        # 检查对象是否有owner属性
        if hasattr(obj, 'owner'):
            return obj.owner == request.user

        # 检查对象是否有user属性（备用）
        if hasattr(obj, 'user'):
            return obj.user == request.user

        # 特殊处理：ScheduledTask 通过 content_object (Account) 关联到用户
        if hasattr(obj, 'content_object') and obj.content_object:
            content_obj = obj.content_object
            if hasattr(content_obj, 'owner'):
                return content_obj.owner == request.user

        # 如果没有owner或user属性，拒绝访问
        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    自定义权限类：只允许用户修改自己的数据，但可以读取所有数据
    """

    def has_permission(self, request, view):
        """检查是否有权限访问视图"""
        # 需要用户认证
        if not request.user or not request.user.is_authenticated:
            return False

        # 管理员有完全权限
        if request.user.is_staff or request.user.is_superuser:
            return True

        # 普通用户可以访问
        return True

    def has_object_permission(self, request, view, obj):
        """检查是否有权限操作特定对象"""
        # 管理员有完全权限
        if request.user.is_staff or request.user.is_superuser:
            return True

        # 读取权限：所有认证用户都可以读取
        if request.method in permissions.SAFE_METHODS:
            return True

        # 写入权限：只能操作自己的数据
        if hasattr(obj, 'owner'):
            return obj.owner == request.user

        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    自定义权限类：管理员有完全权限，普通用户只能读取
    """

    def has_permission(self, request, view):
        """检查是否有权限访问视图"""
        # 需要用户认证
        if not request.user or not request.user.is_authenticated:
            return False

        # 管理员有完全权限
        if request.user.is_staff or request.user.is_superuser:
            return True

        # 普通用户只能读取
        if request.method in permissions.SAFE_METHODS:
            return True

        return False

    def has_object_permission(self, request, view, obj):
        """检查是否有权限操作特定对象"""
        # 管理员有完全权限
        if request.user.is_staff or request.user.is_superuser:
            return True

        # 普通用户只能读取
        if request.method in permissions.SAFE_METHODS:
            return True

        return False


class TemplatePermission(permissions.BasePermission):
    """
    模板权限控制：
    - 未登录用户只能查看官方模板
    - 登录用户可以查看官方模板、公开模板和自己的模板
    - 只有所有者或管理员可以修改/删除模板
    - 所有登录用户都可以应用模板到自己的账户
    """
    def has_permission(self, request, view):
        # 允许所有用户查看模板列表和详情
        if request.method in permissions.SAFE_METHODS:
            return True

        # 只有登录用户可以创建模板或应用模板
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # 允许所有用户查看官方模板
        if request.method in permissions.SAFE_METHODS:
            return obj.is_official or obj.is_public or obj.owner == request.user

        # apply action: 所有登录用户都可以应用模板
        if hasattr(view, 'action') and view.action == 'apply':
            return request.user.is_authenticated

        # 只有所有者或管理员可以修改/删除模板
        return obj.owner == request.user or request.user.is_superuser


class AnonymousReadOnlyPermission(permissions.BasePermission):
    """
    匿名用户只读权限：允许匿名用户读取数据，但只有认证用户可以写入
    """

    def has_permission(self, request, view):
        """检查是否有权限访问视图"""
        # 允许所有用户进行读取操作
        if request.method in permissions.SAFE_METHODS:
            return True

        # 只有认证用户可以写入
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """检查是否有权限操作特定对象"""
        # 允许所有用户读取
        if request.method in permissions.SAFE_METHODS:
            return True

        # 只有认证用户可以写入
        return request.user.is_authenticated
