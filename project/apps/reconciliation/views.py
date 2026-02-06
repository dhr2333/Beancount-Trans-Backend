"""
对账模块的视图集
"""
import logging
from datetime import date
from decimal import Decimal

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend

from project.apps.common.permissions import IsOwnerOrAdminReadWriteOnly
from project.apps.common.filters import ScheduledTaskUserFilterBackend

from .models import ScheduledTask
from .serializers import (
    ScheduledTaskSerializer,
    ScheduledTaskListSerializer,
    ScheduledTaskUpdateSerializer,
    ReconciliationStartSerializer,
    ReconciliationExecuteSerializer,
    ReconciliationExecuteResponseSerializer,
    ReconciliationDuplicateSerializer,
    ReconciliationCommentResponseSerializer,
    ReconciliationUncommentResponseSerializer
)
from .services import (
    BalanceCalculationService,
    ReconciliationService,
    ReconciliationCommentService
)

logger = logging.getLogger(__name__)


class ScheduledTaskViewSet(ModelViewSet):
    """
    待办任务视图集
    
    提供待办任务的增删改查功能，以及对账相关的自定义 action
    """
    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer
    permission_classes = [IsOwnerOrAdminReadWriteOnly]
    authentication_classes = [JWTAuthentication]
    filter_backends = [ScheduledTaskUserFilterBackend, DjangoFilterBackend]
    
    def get_serializer_class(self):
        """根据操作类型返回不同的序列化器"""
        if self.action == 'list':
            return ScheduledTaskListSerializer
        elif self.action == 'retrieve':
            return ScheduledTaskListSerializer
        elif self.action in ['update', 'partial_update']:
            return ScheduledTaskUpdateSerializer
        elif self.action == 'start':
            return ReconciliationStartSerializer
        elif self.action == 'execute':
            return ReconciliationExecuteSerializer
        return ScheduledTaskSerializer
    
    def get_queryset(self):
        """获取查询集
        
        用户过滤由 ScheduledTaskUserFilterBackend 处理
        可通过查询参数过滤：
        - status: 状态筛选（pending/completed/cancelled）
        - task_type: 任务类型筛选（reconciliation/ai_feedback）
        - due: 是否到期（true 返回 scheduled_date <= today 的待办）
        """
        queryset = super().get_queryset()  # 过滤器后端已处理用户过滤
        
        # 到期筛选（优先处理，因为会限制状态）
        due = self.request.query_params.get('due')
        if due and due.lower() == 'true':
            # 到期筛选：scheduled_date <= today 且 status = pending
            queryset = queryset.filter(
                scheduled_date__lte=date.today(),
                status='pending'
            )
        else:
            # 如果没有 due 参数，才应用 status 筛选
            status_param = self.request.query_params.get('status')
            if status_param:
                queryset = queryset.filter(status=status_param)
        
        # 任务类型筛选
        task_type = self.request.query_params.get('task_type')
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        
        return queryset.select_related('content_type').order_by('scheduled_date')
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """开始对账：计算并返回预期余额"""
        task = self.get_object()
        
        if task.task_type != 'reconciliation':
            return Response(
                {'error': '该待办不是对账任务'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if task.status != 'pending':
            return Response(
                {'error': '该待办已完成或已取消'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        account = task.content_object
        
        # 计算预期余额（只计算到当天的记录，明天之后的记录不计入）
        as_of_date = date.today()
        balances = BalanceCalculationService.calculate_balance(
            account.owner,
            account.account,
            as_of_date=as_of_date
        )
        
        # 过滤出所有有余额的币种（余额不为0）
        non_zero_balances = [
            {
                'currency': currency,
                'expected_balance': balance
            }
            for currency, balance in balances.items()
            if balance != Decimal('0.00')
        ]
        
        # 确定默认币种：优先选择CNY，否则选择第一个币种
        default_currency = None
        if non_zero_balances:
            # 查找CNY
            cny_balance = next(
                (item for item in non_zero_balances if item['currency'] == 'CNY'),
                None
            )
            if cny_balance:
                default_currency = 'CNY'
            else:
                default_currency = non_zero_balances[0]['currency']
        
        # 获取上一次对账日期（最近一次完成的对账任务的 as_of_date）
        from django.contrib.contenttypes.models import ContentType
        from project.apps.account.models import Account
        account_content_type = ContentType.objects.get_for_model(Account)
        last_reconciliation = ScheduledTask.objects.filter(
            task_type='reconciliation',
            content_type=account_content_type,
            object_id=account.id,
            status='completed',
            as_of_date__isnull=False
        ).exclude(id=task.id).order_by('-as_of_date').first()
        
        last_reconciliation_date = last_reconciliation.as_of_date if last_reconciliation else None
        
        data = {
            'balances': non_zero_balances,
            'account_name': account.account,
            'as_of_date': date.today(),
            'default_currency': default_currency,
            'is_first_reconciliation': account.is_first_reconciliation(),
            'last_reconciliation_date': last_reconciliation_date
        }
        
        serializer = ReconciliationStartSerializer(data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行对账：处理差额，生成指令，更新状态，创建下一个待办"""
        task = self.get_object()
        
        if task.task_type != 'reconciliation':
            return Response(
                {'error': '该待办不是对账任务'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if task.status != 'pending':
            return Response(
                {'error': '该待办已完成或已取消'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 验证请求数据
        serializer = ReconciliationExecuteSerializer(
            data=request.data,
            context={'task': task}
        )
        serializer.is_valid(raise_exception=True)
        
        # 执行对账
        try:
            result = ReconciliationService.execute_reconciliation(
                task=task,
                actual_balance=serializer.validated_data['actual_balance'],
                currency=serializer.validated_data.get('currency', 'CNY'),
                transaction_items=serializer.validated_data.get('transaction_items', []),
                as_of_date=serializer.validated_data.get('as_of_date')
            )
            
            response_serializer = ReconciliationExecuteResponseSerializer(result)
            return Response(response_serializer.data)
            
        except Exception as e:
            logger.error(f"执行对账失败: {e}", exc_info=True)
            return Response(
                {'error': f'执行对账失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # @action(detail=False, methods=['get'])
    # def check_duplicates(self, request):
    #     """检测重复条目（GET）
        
    #     检测 trans/reconciliation.bean 与 Git 仓库数据的重复条目。
    #     """
    #     try:
    #         result = ReconciliationCommentService.detect_duplicate_entries(request.user)
    #         serializer = ReconciliationDuplicateSerializer(result)
    #         return Response(serializer.data)
    #     except Exception as e:
    #         logger.error(f"检测重复条目失败: {e}", exc_info=True)
    #         return Response(
    #             {'error': f'检测失败: {str(e)}'},
    #             status=status.HTTP_500_INTERNAL_SERVER_ERROR
    #         )
    
    @action(detail=False, methods=['post'])
    def comment_duplicates(self, request):
        """注释重复条目（POST）
        
        自动检测并注释 trans/reconciliation.bean 中与 Git 仓库重复的条目。
        """
        try:
            result = ReconciliationCommentService.detect_and_comment_duplicates(request.user)
            serializer = ReconciliationCommentResponseSerializer(result)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"注释重复条目失败: {e}", exc_info=True)
            return Response(
                {'error': f'注释失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def uncomment_all(self, request):
        """取消所有注释（POST）
        
        取消 trans/reconciliation.bean 中所有对账条目的注释。
        """
        try:
            uncommented_count = ReconciliationCommentService.uncomment_all_entries(request.user)
            result = {
                'uncommented_count': uncommented_count,
                'message': f'已取消 {uncommented_count} 个条目的注释'
            }
            serializer = ReconciliationUncommentResponseSerializer(result)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"取消注释失败: {e}", exc_info=True)
            return Response(
                {'error': f'取消注释失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
