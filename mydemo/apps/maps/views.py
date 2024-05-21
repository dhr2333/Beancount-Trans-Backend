from maps.serializers import AssetsSerializer, ExpenseSerializer, IncomeSerializer
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from translate.models import Expense, Assets, Income
from .filters import CurrentUserFilterBackend
from .permissions import IsOwnerOrAdminReadWriteOnly


class ExpenseViewSet(ModelViewSet):
    """
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
        serializer = self.get_serializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)

        if isinstance(request.data, list):  # 如果是列表，则删除原有数据，保存新数据
            Expense.objects.filter(owner_id=self.request.user).delete()
            serializer.save(owner=self.request.user)
            return Response(serializer.data)
        else:
            return super().create(request, *args, **kwargs)  # 如果不是列表，则调用父类方法

    @action(methods=['get'], detail=False)
    def latest(self, request):
        expense = Expense.objects.latest('id')
        serializer = self.get_serializer(expense)
        return Response(serializer.data)

    def perform_create(self, serializer):
        if self.request.user.is_anonymous:
            raise PermissionDenied("Permission denied. Please log in.")

        if Expense.objects.filter(owner_id=self.request.user, key=self.request.data["key"]).exists():
            raise ValidationError("Account already exists.")
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        if Expense.objects.filter(owner_id=self.request.user, key=self.request.data["key"]).exclude(
                id=instance.id).exists():
            raise ValidationError("Account already exists.")
        serializer.save(owner=self.request.user)
    

class AssetsViewSet(ModelViewSet):
    """
    list:
    返回资产映射列表数据
    retrieve:
    返回资产映射详情数据
    latest:
    返回最新的资产映射数据
    read:
    修改资产映射
    """
    queryset = Assets.objects.all()
    serializer_class = AssetsSerializer
    permission_classes = [IsOwnerOrAdminReadWriteOnly]
    filter_backends = [CurrentUserFilterBackend]
    search_fields = ['full']
    ordering_fields = ['id', 'full']
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)

        if isinstance(request.data, list):
            Assets.objects.filter(owner_id=self.request.user).delete()
            serializer.save(owner=self.request.user)
            return Response(serializer.data)
        else:
            return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        if Assets.objects.filter(owner_id=self.request.user, key=self.request.data["key"]).exists():
            raise ValidationError("Account already exists.")
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        if Assets.objects.filter(owner_id=self.request.user, key=self.request.data["key"]).exclude(
                id=instance.id).exists():
            raise ValidationError("Account already exists.")
        serializer.save(owner=self.request.user)


class IncomeViewSet(ModelViewSet):
    """
    list:
    返回收入映射列表数据
    retrieve:
    返回收入映射详情数据
    latest:
    返回最新的收入映射数据
    read:
    修改收入映射
    """

    queryset = Income.objects.all()
    serializer_class = IncomeSerializer
    permission_classes = [IsOwnerOrAdminReadWriteOnly]
    filter_backends = [CurrentUserFilterBackend]
    search_fields = ['key']
    ordering_fields = ['id', 'key']
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)

        if isinstance(request.data, list):
            Income.objects.filter(owner_id=self.request.user).delete()
            serializer.save(owner=self.request.user)
            return Response(serializer.data)
        else:
            return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        if Income.objects.filter(owner_id=self.request.user, key=self.request.data["key"]).exists():
            raise ValidationError("Account already exists.")
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        if Income.objects.filter(owner_id=self.request.user, key=self.request.data["key"]).exclude(
                id=instance.id).exists():
            raise ValidationError("Accountalready exists.")
        serializer.save(owner=self.request.user)
