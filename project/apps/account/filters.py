import django_filters
from django.db import models
from django.contrib.auth.models import User
from rest_framework.filters import BaseFilterBackend
from .models import Account, Currency


class CurrentUserFilterBackend(BaseFilterBackend):
    """当前用户过滤器"""
    
    def filter_queryset(self, request, queryset, view):
        """只返回当前用户的账户"""
        if request.user.is_authenticated:
            return queryset.filter(owner=request.user)
        return queryset.none()


class AccountTypeFilter(django_filters.FilterSet):
    """账户类型过滤器"""
    
    account_type = django_filters.ChoiceFilter(
        choices=[
            ('Assets', '资产账户'),
            ('Liabilities', '负债账户'),
            ('Equity', '权益账户'),
            ('Income', '收入账户'),
            ('Expenses', '支出账户'),
        ],
        method='filter_by_account_type',
        help_text="按账户类型过滤"
    )
    
    enable = django_filters.BooleanFilter(
        help_text="按启用状态过滤"
    )
    
    has_children = django_filters.BooleanFilter(
        method='filter_has_children',
        help_text="是否有子账户"
    )
    
    has_mappings = django_filters.BooleanFilter(
        method='filter_has_mappings',
        help_text="是否有相关映射"
    )
    
    currency = django_filters.ModelChoiceFilter(
        queryset=Currency.objects.all(),
        method='filter_by_currency',
        help_text="按货币过滤"
    )
    
    search = django_filters.CharFilter(
        method='filter_search',
        help_text="搜索账户名称"
    )
    
    class Meta:
        model = Account
        fields = ['account_type', 'enable', 'has_children', 'has_mappings', 'currency', 'search']
    
    def filter_by_account_type(self, queryset, name, value):
        """按账户类型过滤"""
        return queryset.filter(account__startswith=value)
    
    def filter_has_children(self, queryset, name, value):
        """按是否有子账户过滤"""
        if value:
            return queryset.filter(children__isnull=False).distinct()
        else:
            return queryset.filter(children__isnull=True)
    
    def filter_has_mappings(self, queryset, name, value):
        """按是否有相关映射过滤"""
        from django.apps import apps
        
        try:
            Expense = apps.get_model('maps', 'Expense')
            Assets = apps.get_model('maps', 'Assets')
            Income = apps.get_model('maps', 'Income')
            
            if value:
                # 有映射的账户
                expense_accounts = Expense.objects.filter(enable=True).values_list('expend_id', flat=True)
                assets_accounts = Assets.objects.filter(enable=True).values_list('assets_id', flat=True)
                income_accounts = Income.objects.filter(enable=True).values_list('income_id', flat=True)
                
                all_mapped_accounts = set(expense_accounts) | set(assets_accounts) | set(income_accounts)
                return queryset.filter(id__in=all_mapped_accounts)
            else:
                # 没有映射的账户
                expense_accounts = Expense.objects.filter(enable=True).values_list('expend_id', flat=True)
                assets_accounts = Assets.objects.filter(enable=True).values_list('assets_id', flat=True)
                income_accounts = Income.objects.filter(enable=True).values_list('income_id', flat=True)
                
                all_mapped_accounts = set(expense_accounts) | set(assets_accounts) | set(income_accounts)
                return queryset.exclude(id__in=all_mapped_accounts)
        except:
            # 如果映射模型不存在，返回空查询集
            return queryset.none()
    
    def filter_by_currency(self, queryset, name, value):
        """按货币过滤"""
        return queryset.filter(currencies=value)
    
    def filter_search(self, queryset, name, value):
        """搜索账户名称"""
        return queryset.filter(account__icontains=value)


class CurrencyFilter(django_filters.FilterSet):
    """货币过滤器"""
    
    search = django_filters.CharFilter(
        method='filter_search',
        help_text="搜索货币代码或名称"
    )
    
    class Meta:
        model = Currency
        fields = ['search']
    
    def filter_search(self, queryset, name, value):
        """搜索货币代码或名称"""
        return queryset.filter(
            models.Q(code__icontains=value) | models.Q(name__icontains=value)
        )
