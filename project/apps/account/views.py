from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import transaction
# from django.shortcuts import get_object_or_404
from django.apps import apps

from project.apps.account.models import Account, Currency
from project.apps.account.serializers import (
    AccountSerializer, AccountTreeSerializer, CurrencySerializer,
    AccountBatchUpdateSerializer, AccountMigrationSerializer, AccountDeleteSerializer
)
from project.apps.account.filters import AccountTypeFilter
from django_filters.rest_framework import DjangoFilterBackend
from project.apps.common.permissions import IsOwnerOrAdminReadWriteOnly
from project.apps.common.filters import CurrentUserFilterBackend


class CurrencyViewSet(ModelViewSet):
    """货币管理视图集"""
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = [IsOwnerOrAdminReadWriteOnly]
    filter_backends = [CurrentUserFilterBackend]
    authentication_classes = [JWTAuthentication]
    search_fields = ['code', 'name']
    ordering_fields = ['code', 'name']
    ordering = ['code']
    
    def perform_create(self, serializer):
        """创建货币时设置属主"""
        serializer.save(owner=self.request.user)


class AccountViewSet(ModelViewSet):
    """
    账户管理视图集
    
    提供基于Beancount的树形账户管理功能，包括：
    - 账户的增删改查
    - 树形结构展示
    - 账户迁移
    - 账户映射
    """
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [IsOwnerOrAdminReadWriteOnly]
    filter_backends = [CurrentUserFilterBackend, DjangoFilterBackend]
    filterset_class = AccountTypeFilter
    authentication_classes = [JWTAuthentication]
    search_fields = ['account']
    ordering_fields = ['account', 'created', 'modified']
    ordering = ['account']
    
    def get_serializer_class(self):
        """根据操作类型返回不同的序列化器"""
        if self.action == 'tree':
            return AccountTreeSerializer
        elif self.action == 'batch_update':
            return AccountBatchUpdateSerializer
        elif self.action == 'migrate':
            return AccountMigrationSerializer
        return AccountSerializer
    
    def get_queryset(self):
        """获取查询集"""
        queryset = super().get_queryset()
        
        # 根据用户过滤
        if self.request.user.is_authenticated:
            queryset = queryset.filter(owner=self.request.user)
        
        # 根据账户类型过滤
        account_type = self.request.query_params.get('account_type')
        if account_type:
            queryset = queryset.filter(account__startswith=account_type)
        
        # 根据启用状态过滤
        enable = self.request.query_params.get('enable')
        if enable is not None:
            queryset = queryset.filter(enable=enable.lower() == 'true')
        
        return queryset.select_related('parent', 'owner').prefetch_related('currencies')
    
    def perform_create(self, serializer):
        """创建账户时设置属主"""
        serializer.save(owner=self.request.user)
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """获取账户树形结构"""
        root_accounts = self.get_queryset().filter(parent__isnull=True)
        
        serializer = self.get_serializer(root_accounts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def mappings(self, request, pk=None):
        """获取账户相关的映射"""
        account = self.get_object()

        try:
            Expense = apps.get_model('maps', 'Expense')
            Assets = apps.get_model('maps', 'Assets')
            Income = apps.get_model('maps', 'Income')

            # 只获取当前用户的映射
            expense_mappings = Expense.objects.filter(
                expend=account, 
                owner=request.user, 
                # enable=True
            )
            assets_mappings = Assets.objects.filter(
                assets=account, 
                owner=request.user, 
                # enable=True
            )
            income_mappings = Income.objects.filter(
                income=account, 
                owner=request.user, 
                # enable=True
            )

            result = {
                'account': account.account,
                'account_id': account.id,
                'expense_mappings': [
                    {
                        'id': m.id, 
                        'key': m.key, 
                        'payee': m.payee,
                        'currency': m.currency.code if m.currency else None,
                        'enable': m.enable
                    }
                    for m in expense_mappings
                ],
                'assets_mappings': [
                    {
                        'id': m.id, 
                        'key': m.key, 
                        'full': m.full,
                        'enable': m.enable
                    }
                    for m in assets_mappings
                ],
                'income_mappings': [
                    {
                        'id': m.id, 
                        'key': m.key, 
                        'payer': m.payer,
                        'enable': m.enable
                    }
                    for m in income_mappings
                ],
                'total_count': expense_mappings.count() + assets_mappings.count() + income_mappings.count()
            }

            return Response(result)
        except Exception as e:
            return Response(
                {'error': f'获取映射失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, pk=None):
        """删除账户（需要提供迁移目标账户）"""
        account = self.get_object()
        
        # 验证请求数据
        serializer = AccountDeleteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        migrate_to_id = serializer.validated_data['migrate_to']
        
        try:
            migrate_to = Account.objects.get(id=migrate_to_id, owner=request.user)
        except Account.DoesNotExist:
            return Response(
                {'error': '目标账户不存在或无权访问'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                result = account.delete_with_migration(migrate_to=migrate_to)
                return Response({
                    'message': '账户删除成功',
                    'result': result
                })
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'删除账户失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def migration_candidates(self, request, pk=None):
        """获取可用的迁移目标账户列表"""
        account = self.get_object()
        
        # 获取启用的账户（所有类型账户）作为迁移候选
        account_type = account.account.split(':')[0]
        candidates = Account.objects.filter(
            owner=request.user,
            enable=True
        ).exclude(
            id=account.id,
            account__startswith=account_type
        ).order_by('account')
        
        serializer = AccountSerializer(candidates, many=True, context={'request': request})
        return Response({
            'candidates': serializer.data,
            'current_account': {
                'id': account.id,
                'account': account.account,
                'account_type': account.get_account_type()
            }
        })
