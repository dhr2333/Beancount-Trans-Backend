from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.apps import apps

from project.apps.tags.models import Tag
from project.apps.tags.serializers import (
    TagSerializer, 
    TagTreeSerializer,
    TagBatchUpdateSerializer, 
    TagDeleteSerializer
)
from project.apps.tags.filters import TagFilter
from project.apps.common.permissions import IsOwnerOrAdminReadWriteOnly, AnonymousReadOnlyPermission
from project.apps.common.filters import CurrentUserFilterBackend, AnonymousUserFilterBackend


class TagViewSet(ModelViewSet):
    """
    标签管理视图集
    
    提供标签管理功能，包括：
    - 标签的增删改查
    - 树形结构展示
    - 批量操作
    
    支持匿名用户访问id=1用户的数据（只读）
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AnonymousReadOnlyPermission]
    filter_backends = [AnonymousUserFilterBackend, DjangoFilterBackend]
    filterset_class = TagFilter
    authentication_classes = [JWTAuthentication]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created', 'modified']
    ordering = ['name']
    
    def get_serializer_class(self):
        """根据操作类型返回不同的序列化器"""
        if self.action == 'tree':
            return TagTreeSerializer
        elif self.action == 'batch_update':
            return TagBatchUpdateSerializer
        return TagSerializer
    
    def get_queryset(self):
        """获取查询集"""
        queryset = super().get_queryset()
        
        # 根据用户过滤，匿名用户使用id=1用户的数据
        User = get_user_model()
        if self.request.user.is_authenticated:
            queryset = queryset.filter(owner=self.request.user)
        else:
            # 匿名用户使用id=1用户的标签
            try:
                default_user = User.objects.get(id=1)
                queryset = queryset.filter(owner=default_user)
            except User.DoesNotExist:
                queryset = queryset.none()
        
        # 根据启用状态过滤
        enable = self.request.query_params.get('enable')
        if enable is not None:
            queryset = queryset.filter(enable=enable.lower() == 'true')
        
        return queryset.select_related('parent', 'owner')
    
    def perform_create(self, serializer):
        """创建标签时设置属主"""
        try:
            serializer.save(owner=self.request.user)
        except DjangoValidationError as e:
            raise ValidationError({'detail': str(e)})
    
    def perform_update(self, serializer):
        """更新标签时进行验证"""
        try:
            serializer.save()
        except DjangoValidationError as e:
            raise ValidationError({'detail': str(e)})
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """
        获取标签树形结构
        
        返回所有根标签及其子标签的树形结构
        """
        root_tags = self.get_queryset().filter(parent__isnull=True)
        
        serializer = self.get_serializer(root_tags, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        """
        获取指定标签的直接子标签
        
        Args:
            pk: 标签ID
        
        Returns:
            子标签列表
        """
        tag = self.get_object()
        children = tag.children.filter(owner=request.user if request.user.is_authenticated else 1)
        
        serializer = TagSerializer(children, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def descendants(self, request, pk=None):
        """
        获取指定标签的所有后代标签（递归）
        
        Args:
            pk: 标签ID
        
        Returns:
            所有后代标签的ID列表
        """
        tag = self.get_object()
        descendant_ids = tag.get_all_children()
        
        return Response({
            'tag_id': tag.id,
            'tag_name': tag.name,
            'descendant_ids': descendant_ids,
            'count': len(descendant_ids)
        })
    
    @action(detail=True, methods=['post'])
    def toggle_enable(self, request, pk=None):
        """
        切换标签的启用状态
        
        注意：禁用父标签会自动禁用所有子标签
        """
        tag = self.get_object()
        
        with transaction.atomic():
            tag.enable = not tag.enable
            tag.save()
        
        serializer = self.get_serializer(tag)
        return Response({
            'message': f"标签已{'启用' if tag.enable else '禁用'}",
            'tag': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def batch_update(self, request):
        """
        批量更新标签
        
        支持的操作：
        - enable: 启用标签
        - disable: 禁用标签
        - delete: 删除标签
        
        请求体示例:
        {
            "tag_ids": [1, 2, 3],
            "action": "disable"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tag_ids = serializer.validated_data['tag_ids']
        action_type = serializer.validated_data['action']
        
        # 获取用户的标签
        User = get_user_model()
        if request.user.is_authenticated:
            user = request.user
        else:
            try:
                user = User.objects.get(id=1)
            except User.DoesNotExist:
                return Response(
                    {'error': '默认用户（ID=1）不存在'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        tags = Tag.objects.filter(id__in=tag_ids, owner=user)
        
        if not tags.exists():
            return Response(
                {'error': '未找到指定的标签'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        result = {
            'action': action_type,
            'affected_count': 0,
            'tag_ids': []
        }
        
        try:
            with transaction.atomic():
                if action_type == 'enable':
                    tags.update(enable=True)
                    result['affected_count'] = tags.count()
                    result['tag_ids'] = list(tags.values_list('id', flat=True))
                    
                elif action_type == 'disable':
                    # 禁用标签及其所有子标签
                    all_tag_ids = []
                    for tag in tags:
                        all_tag_ids.append(tag.id)
                        all_tag_ids.extend(tag.get_all_children())
                    
                    Tag.objects.filter(id__in=all_tag_ids).update(enable=False)
                    result['affected_count'] = len(all_tag_ids)
                    result['tag_ids'] = all_tag_ids
                    
                elif action_type == 'delete':
                    # 删除标签（CASCADE会自动删除子标签）
                    tag_ids_to_delete = list(tags.values_list('id', flat=True))
                    tags.delete()
                    result['affected_count'] = len(tag_ids_to_delete)
                    result['tag_ids'] = tag_ids_to_delete
            
            return Response({
                'message': '批量操作成功',
                'result': result
            })
            
        except Exception as e:
            return Response(
                {'error': f'批量操作失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, pk=None):
        """
        删除标签
        
        请求体（可选）:
        {
            "force": false  # 是否强制删除（包括子标签）
        }
        """
        tag = self.get_object()
        
        # 验证请求数据
        serializer = TagDeleteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        force = serializer.validated_data.get('force', False)
        
        # 检查是否有子标签
        if tag.has_children() and not force:
            return Response(
                {
                    'error': '标签存在子标签，无法删除',
                    'hint': '请先删除子标签，或使用 force=true 强制删除',
                    'children_count': tag.children.count()
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                result = tag.delete_with_children(force=force)
                return Response({
                    'message': '标签删除成功',
                    'result': result
                })
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'删除标签失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def mappings(self, request, pk=None):
        """获取标签相关的映射"""
        tag = self.get_object()

        try:
            Expense = apps.get_model('maps', 'Expense')
            Assets = apps.get_model('maps', 'Assets')
            Income = apps.get_model('maps', 'Income')

            # 获取当前用户的映射，匿名用户使用id=1用户的映射
            User = get_user_model()
            if request.user.is_authenticated:
                user = request.user
            else:
                # 匿名用户使用id=1用户的映射
                try:
                    user = User.objects.get(id=1)
                except User.DoesNotExist:
                    return Response(
                        {'error': '默认用户（ID=1）不存在'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            # 通过多对多关系获取包含该标签的映射
            expense_mappings = Expense.objects.filter(
                tags=tag, 
                owner=user
            )
            assets_mappings = Assets.objects.filter(
                tags=tag, 
                owner=user
            )
            income_mappings = Income.objects.filter(
                tags=tag, 
                owner=user
            )

            result = {
                'tag': tag.get_full_path(),
                'tag_id': tag.id,
                'expense_mappings': [
                    {
                        'id': m.id, 
                        'key': m.key, 
                        'payee': m.payee,
                        'account': m.expend.account if m.expend else None,
                        'currency': m.currency,
                        'enable': m.enable
                    }
                    for m in expense_mappings
                ],
                'assets_mappings': [
                    {
                        'id': m.id, 
                        'key': m.key, 
                        'full': m.full,
                        'account': m.assets.account if m.assets else None,
                        'enable': m.enable
                    }
                    for m in assets_mappings
                ],
                'income_mappings': [
                    {
                        'id': m.id, 
                        'key': m.key, 
                        'payer': m.payer,
                        'account': m.income.account if m.income else None,
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
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        获取标签统计信息
        
        返回：
        - 总标签数
        - 启用的标签数
        - 根标签数
        - 子标签数
        """
        queryset = self.get_queryset()
        
        total = queryset.count()
        enabled = queryset.filter(enable=True).count()
        root = queryset.filter(parent__isnull=True).count()
        children = queryset.filter(parent__isnull=False).count()
        
        return Response({
            'total': total,
            'enabled': enabled,
            'disabled': total - enabled,
            'root_tags': root,
            'child_tags': children
        })
