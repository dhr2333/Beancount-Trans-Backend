from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
# from project.utils.tools import get_user_config
from project.apps.maps.models import Expense, Assets, Income
from project.apps.maps.filters import CurrentUserFilterBackend
from project.apps.maps.permissions import IsOwnerOrAdminReadWriteOnly
from project.apps.maps.serializers import AssetsSerializer, ExpenseSerializer, IncomeSerializer


class ExpenseViewSet(ModelViewSet):
    """
    支出映射管理视图集
    
    提供支出映射的增删改查功能，支持批量操作。
    所有操作都需要用户认证，且只能操作自己的数据。
    
    list:
    返回支出映射列表数据
    create:
    创建一条新的支出映射数据
    retrieve:
    返回支出映射详情数据
    latest:
    返回最新的支出映射数据
    update:
    更新指定条目支出映射
    delete:
    删除指定支出映射条目
    """
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [IsOwnerOrAdminReadWriteOnly]
    filter_backends = [CurrentUserFilterBackend]
    search_fields = ['key', 'payee']
    ordering_fields = ['id', 'key']
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):  # 重写create方法，实现批量创建
        if self.request.user.is_anonymous:
            raise PermissionDenied("Permission denied. Please log in.")

        serializer = self.get_serializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)

        if isinstance(request.data, list):  # 如果是列表，则删除原有数据，保存新数据
            Expense.objects.filter(owner_id=self.request.user).delete()
            serializer.save(owner=self.request.user)
            return Response(serializer.data)
        else:
            return super().create(request, *args, **kwargs)  # 如果不是列表，则调用父类方法

    # @action(methods=['get'], detail=False)
    # def latest(self, request):
    #     expense = Expense.objects.latest('id')
    #     serializer = self.get_serializer(expense)
    #     return Response(serializer.data)

    def perform_create(self, serializer):
        if self.request.user.is_anonymous:
            raise PermissionDenied("Permission denied. Please log in.")

        if Expense.objects.filter(owner_id=self.request.user, key=self.request.data["key"]).exists():
            raise ValidationError("Account already exists.")
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        key = self.request.data.get('key', instance.key)
        if Expense.objects.filter(owner_id=self.request.user, key=key).exclude(
                id=instance.id).exists():
            raise ValidationError("Account already exists.")
        serializer.save(owner=self.request.user)


class AssetsViewSet(ModelViewSet):
    """
    资产映射管理视图集
    
    提供资产映射的增删改查功能，支持批量操作。
    所有操作都需要用户认证，且只能操作自己的数据。
    """
    queryset = Assets.objects.all()
    serializer_class = AssetsSerializer
    permission_classes = [IsOwnerOrAdminReadWriteOnly]
    filter_backends = [CurrentUserFilterBackend]
    search_fields = ['full']
    ordering_fields = ['id', 'full']
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        if self.request.user.is_anonymous:
            raise PermissionDenied("Permission denied. Please log in.")

        serializer = self.get_serializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)

        if isinstance(request.data, list):
            Assets.objects.filter(owner_id=self.request.user).delete()
            serializer.save(owner=self.request.user)
            return Response(serializer.data)
        else:
            return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        if self.request.user.is_anonymous:
            raise PermissionDenied("Permission denied. Please log in.")

        if Assets.objects.filter(owner_id=self.request.user, key=self.request.data["key"]).exists():
            raise ValidationError("Account already exists.")
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        key = self.request.data.get('key', instance.key)
        if Assets.objects.filter(owner_id=self.request.user, key=key).exclude(
                id=instance.id).exists():
            raise ValidationError("Account already exists.")
        serializer.save(owner=self.request.user)


class IncomeViewSet(ModelViewSet):
    queryset = Income.objects.all()
    serializer_class = IncomeSerializer
    permission_classes = [IsOwnerOrAdminReadWriteOnly]
    filter_backends = [CurrentUserFilterBackend]
    search_fields = ['key']
    ordering_fields = ['id', 'key']
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        if self.request.user.is_anonymous:
            raise PermissionDenied("Permission denied. Please log in.")

        serializer = self.get_serializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)

        if isinstance(request.data, list):
            Income.objects.filter(owner_id=self.request.user).delete()
            serializer.save(owner=self.request.user)
            return Response(serializer.data)
        else:
            return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        if self.request.user.is_anonymous:
            raise PermissionDenied("Permission denied. Please log in.")

        if Income.objects.filter(owner_id=self.request.user, key=self.request.data["key"]).exists():
            raise ValidationError("Account already exists.")
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        key = self.request.data.get('key', instance.key)
        if Income.objects.filter(owner_id=self.request.user, key=key).exclude(
                id=instance.id).exists():
            raise ValidationError("Accountalready exists.")
        serializer.save(owner=self.request.user)




