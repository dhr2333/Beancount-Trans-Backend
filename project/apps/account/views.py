from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.apps import apps

from .models import Account, Currency
from .serializers import (
    AccountSerializer, AccountTreeSerializer, CurrencySerializer,
    AccountBatchUpdateSerializer, AccountMigrationSerializer
)
from .filters import AccountTypeFilter
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


class AccountViewSet(ModelViewSet):
    """
    账户管理视图集
    
    提供基于Beancount的树形账户管理功能，包括：
    - 账户的增删改查
    - 树形结构展示
    - 批量操作
    - 账户迁移
    - 映射管理
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
        # 获取根账户（没有父账户的账户）
        root_accounts = self.get_queryset().filter(parent__isnull=True, enable=True)
        
        serializer = self.get_serializer(root_accounts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """按账户类型分组获取账户"""
        account_type = request.query_params.get('type')
        if not account_type:
            return Response({'error': '请指定账户类型'}, status=status.HTTP_400_BAD_REQUEST)
        
        valid_types = ['Assets', 'Liabilities', 'Equity', 'Income', 'Expenses']
        if account_type not in valid_types:
            return Response(
                {'error': f'无效的账户类型，必须是: {", ".join(valid_types)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        accounts = self.get_queryset().filter(account__startswith=account_type)
        serializer = self.get_serializer(accounts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def mappings(self, request, pk=None):
        """获取账户相关的映射"""
        account = self.get_object()
        
        try:
            Expense = apps.get_model('maps', 'Expense')
            Assets = apps.get_model('maps', 'Assets')
            Income = apps.get_model('maps', 'Income')
            
            expense_mappings = Expense.objects.filter(expend=account, enable=True)
            assets_mappings = Assets.objects.filter(assets=account, enable=True)
            income_mappings = Income.objects.filter(income=account, enable=True)
            
            result = {
                'account': account.account,
                'expense_mappings': [
                    {'id': m.id, 'key': m.key, 'payee': m.payee}
                    for m in expense_mappings
                ],
                'assets_mappings': [
                    {'id': m.id, 'key': m.key, 'full': m.full}
                    for m in assets_mappings
                ],
                'income_mappings': [
                    {'id': m.id, 'key': m.key, 'payer': m.payer}
                    for m in income_mappings
                ]
            }
            
            return Response(result)
        except Exception as e:
            return Response(
                {'error': f'获取映射失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """关闭账户"""
        account = self.get_object()
        migrate_to_id = request.data.get('migrate_to')
        
        migrate_to = None
        if migrate_to_id:
            try:
                migrate_to = Account.objects.get(id=migrate_to_id, owner=request.user)
            except Account.DoesNotExist:
                return Response(
                    {'error': '目标账户不存在'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            result = account.close(migrate_to=migrate_to)
            return Response(result)
        except Exception as e:
            return Response(
                {'error': f'关闭账户失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def batch_update(self, request):
        """批量更新账户"""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        account_ids = data['account_ids']
        action_type = data['action']
        target_account_id = data.get('target_account_id')
        
        # 验证账户所有权
        accounts = Account.objects.filter(id__in=account_ids, owner=request.user)
        if len(accounts) != len(account_ids):
            return Response(
                {'error': '部分账户不存在或无权限'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            with transaction.atomic():
                if action_type == 'enable':
                    accounts.update(enable=True)
                elif action_type == 'disable':
                    accounts.update(enable=False)
                elif action_type == 'close':
                    for account in accounts:
                        account.close()
                elif action_type == 'migrate':
                    if not target_account_id:
                        return Response(
                            {'error': '迁移操作需要指定目标账户'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    target_account = Account.objects.get(id=target_account_id, owner=request.user)
                    for account in accounts:
                        account.close(migrate_to=target_account)
                
                return Response({'message': f'成功{action_type}了{len(accounts)}个账户'})
        
        except Exception as e:
            return Response(
                {'error': f'批量操作失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def migrate(self, request):
        """账户迁移"""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        source_account_id = data['source_account_id']
        target_account_id = data['target_account_id']
        migrate_mappings = data['migrate_mappings']
        close_source = data['close_source']
        
        try:
            with transaction.atomic():
                source_account = Account.objects.get(id=source_account_id, owner=request.user)
                target_account = Account.objects.get(id=target_account_id, owner=request.user)
                
                if migrate_mappings:
                    # 迁移映射
                    try:
                        Expense = apps.get_model('maps', 'Expense')
                        Assets = apps.get_model('maps', 'Assets')
                        Income = apps.get_model('maps', 'Income')
                        
                        expense_count = Expense.objects.filter(expend=source_account).update(expend=target_account)
                        assets_count = Assets.objects.filter(assets=source_account).update(assets=target_account)
                        income_count = Income.objects.filter(income=source_account).update(income=target_account)
                        
                        mappings_migrated = expense_count + assets_count + income_count
                    except Exception as e:
                        return Response(
                            {'error': f'迁移映射失败: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
                else:
                    mappings_migrated = 0
                
                if close_source:
                    source_account.close(migrate_to=target_account)
                
                return Response({
                    'message': '账户迁移成功',
                    'mappings_migrated': mappings_migrated,
                    'source_closed': close_source
                })
        
        except Account.DoesNotExist:
            return Response(
                {'error': '账户不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'迁移失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取账户统计信息"""
        queryset = self.get_queryset()
        
        # 按账户类型统计
        type_stats = {}
        for account_type in ['Assets', 'Liabilities', 'Equity', 'Income', 'Expenses']:
            count = queryset.filter(account__startswith=account_type).count()
            enabled_count = queryset.filter(account__startswith=account_type, enable=True).count()
            type_stats[account_type] = {
                'total': count,
                'enabled': enabled_count,
                'disabled': count - enabled_count
            }
        
        # 总体统计
        total_accounts = queryset.count()
        enabled_accounts = queryset.filter(enable=True).count()
        disabled_accounts = total_accounts - enabled_accounts
        
        # 有映射的账户数量
        try:
            Expense = apps.get_model('maps', 'Expense')
            Assets = apps.get_model('maps', 'Assets')
            Income = apps.get_model('maps', 'Income')
            
            expense_accounts = set(Expense.objects.filter(owner=request.user, enable=True).values_list('expend_id', flat=True))
            assets_accounts = set(Assets.objects.filter(owner=request.user, enable=True).values_list('assets_id', flat=True))
            income_accounts = set(Income.objects.filter(owner=request.user, enable=True).values_list('income_id', flat=True))
            
            mapped_accounts = len(expense_accounts | assets_accounts | income_accounts)
        except:
            mapped_accounts = 0
        
        return Response({
            'total_accounts': total_accounts,
            'enabled_accounts': enabled_accounts,
            'disabled_accounts': disabled_accounts,
            'mapped_accounts': mapped_accounts,
            'type_statistics': type_stats
        })
