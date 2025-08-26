from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
# from project.utils.tools import get_user_config
from project.apps.maps.models import Expense, Assets, Income,Template, TemplateItem
from project.apps.maps.filters import CurrentUserFilterBackend
from project.apps.maps.permissions import IsOwnerOrAdminReadWriteOnly
from project.apps.maps.serializers import AssetsSerializer, ExpenseSerializer, IncomeSerializer, TemplateItemSerializer, TemplateListSerializer, TemplateDetailSerializer
from django.shortcuts import get_object_or_404


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


class TemplateViewSet(ModelViewSet):
    # 移除固定的serializer_class，改为动态选择

    def get_serializer_class(self):
        if self.action == 'list':
            return TemplateListSerializer
        elif self.action == 'retrieve':
            return TemplateDetailSerializer
        return TemplateDetailSerializer  # 对于create/update等操作使用DetailSerializer

    def get_queryset(self):
        # 官方模板对所有用户可见
        queryset = Template.objects.filter(is_official=True)

        # 登录用户可以看到自己的模板和公开模板
        if self.request.user.is_authenticated:
            user_templates = Template.objects.filter(owner=self.request.user)
            public_templates = Template.objects.filter(is_public=True, is_official=False)
            queryset = queryset | user_templates | public_templates

        # 按类型过滤
        template_type = self.request.query_params.get('type', None)
        if template_type:
            queryset = queryset.filter(type=template_type)

        return queryset.distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # 对于列表视图，不需要预取items
        if self.action == 'list':
            return context

        # 对于详情视图，预取items以提高性能
        context['queryset'] = Template.objects.prefetch_related('items')
        return context

    def retrieve(self, request, *args, **kwargs):
        # 使用预取优化查询
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """应用模板到用户映射"""
        template = self.get_object()
        serializer = TemplateApplySerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        action_type = data['action']
        conflict_resolution = data.get('conflict_resolution', 'skip')

        # 根据模板类型应用不同的映射
        if template.type == 'expense':
            self._apply_expense_template(template, action_type, conflict_resolution)
        elif template.type == 'income':
            self._apply_income_template(template, action_type, conflict_resolution)
        elif template.type == 'assets':
            self._apply_assets_template(template, action_type, conflict_resolution)

        return Response({"message": "模板应用成功"})

    def _apply_expense_template(self, template, action_type, conflict_resolution):
        """应用支出模板"""
        if action_type == 'overwrite':
            # 删除用户现有的所有支出映射
            Expense.objects.filter(owner=self.request.user).delete()

        for item in template.items.all():
            # 检查是否已存在相同关键字的映射
            existing = Expense.objects.filter(owner=self.request.user, key=item.key).first()

            if existing:
                if conflict_resolution == 'skip':
                    continue
                elif conflict_resolution == 'overwrite':
                    existing.delete()

            # 创建新的映射
            Expense.objects.create(
                owner=self.request.user,
                key=item.key,
                payee=item.payee,
                expend=item.account,
                currency=item.currency
            )

    def _apply_income_template(self, template, action_type, conflict_resolution):
        """应用收入模板"""
        if action_type == 'overwrite':
            Income.objects.filter(owner=self.request.user).delete()

        for item in template.items.all():
            existing = Income.objects.filter(owner=self.request.user, key=item.key).first()

            if existing:
                if conflict_resolution == 'skip':
                    continue
                elif conflict_resolution == 'overwrite':
                    existing.delete()

            Income.objects.create(
                owner=self.request.user,
                key=item.key,
                payer=item.payer,
                income=item.account
            )

    def _apply_assets_template(self, template, action_type, conflict_resolution):
        """应用资产模板"""
        if action_type == 'overwrite':
            Assets.objects.filter(owner=self.request.user).delete()

        for item in template.items.all():
            existing = Assets.objects.filter(owner=self.request.user, key=item.key).first()

            if existing:
                if conflict_resolution == 'skip':
                    continue
                elif conflict_resolution == 'overwrite':
                    existing.delete()

            Assets.objects.create(
                owner=self.request.user,
                key=item.key,
                full=item.full,
                assets=item.account
            )

class TemplateItemViewSet(ModelViewSet):
    serializer_class = TemplateItemSerializer

    def get_queryset(self):
        return TemplateItem.objects.filter(template__owner=self.request.user)

    def perform_create(self, serializer):
        template_id = self.kwargs.get('template_pk')
        template = get_object_or_404(Template, pk=template_id, owner=self.request.user)
        serializer.save(template=template)
