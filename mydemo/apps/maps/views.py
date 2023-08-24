from maps.serializers import AssetsSerializer, ExpenseSerializer
# from rest_framework import filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from translate.models import Expense, Assets
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
    order:
    修改商家优先级接口
    """
    # authentication_classes = [authentication.IsAuthenticatedOrReadOnly]
    # permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [IsOwnerOrAdminReadWriteOnly]
    # filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    filter_backends = [CurrentUserFilterBackend]
    search_fields = ['key', 'payee']
    ordering_fields = ['id', 'key']

    # pagination_class = LargeResultsSetPagination

    @action(methods=['get'], detail=False)
    def latest(self, request):
        expense = Expense.objects.latest('id')
        serializer = self.get_serializer(expense)
        return Response(serializer.data)

    @action(methods=['put'], detail=True)
    def order(self, request, pk):
        expense = self.get_object()
        expense.payee_order = request.data.get('payee_order')
        expense.save()
        serializer = self.get_serializer(expense)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class AssetsViewSet(ModelViewSet):
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
    # authentication_classes = [IsAuthenticatedOrReadOnly]
    # permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Assets.objects.all()
    serializer_class = AssetsSerializer
    permission_classes = [IsOwnerOrAdminReadWriteOnly]
    # filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    filter_backends = [CurrentUserFilterBackend]
    search_fields = ['full']
    ordering_fields = ['id', 'full']

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

# class ExpenseMapList(generics.ListCreateAPIView):
#     queryset = Expense_Map.objects.all()
#     serializer_class = ExpenseMapSerializer


# class ExpenseMapDetail(generics.RetrieveUpdateDestroyAPIView):
#     queryset = Expense_Map.objects.all()
#     serializer_class = ExpenseMapSerializer


# class AssetsMapList(generics.ListCreateAPIView):
#     """
#     get:
#     返回所有账户信息
#     post:
#     新建账户映射
#     """
#     queryset = Assets_Map.objects.all()
#     serializer_class = AssetsMapSerializer
#
#
# class AssetsMapDetail(generics.RetrieveUpdateDestroyAPIView):
#     queryset = Assets_Map.objects.all()
#     serializer_class = AssetsMapSerializer


# class LargeResultsSetPagination(PageNumberPagination):
#     page_size = 200
#     page_query_param = 'page'
#     page_size_query_param = 'page_size'
#     max_page_size = 200
