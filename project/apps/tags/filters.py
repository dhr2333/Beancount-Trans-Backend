from django_filters import rest_framework as filters
from project.apps.tags.models import Tag


class TagFilter(filters.FilterSet):
    """标签过滤器"""
    
    # 按名称模糊搜索
    name = filters.CharFilter(lookup_expr='icontains', help_text="标签名称（模糊匹配）")
    
    # 按启用状态过滤
    enable = filters.BooleanFilter(help_text="是否启用")
    
    # 按是否有父标签过滤（根标签 vs 子标签）
    is_root = filters.BooleanFilter(method='filter_is_root', help_text="是否为根标签")
    
    # 按父标签ID过滤
    parent = filters.NumberFilter(help_text="父标签ID")
    
    # 按父标签名称过滤
    parent__name = filters.CharFilter(lookup_expr='icontains', help_text="父标签名称（模糊匹配）")
    
    class Meta:
        model = Tag
        fields = ['name', 'enable', 'parent', 'is_root']
    
    def filter_is_root(self, queryset, name, value):
        """
        过滤根标签或子标签
        
        Args:
            value: True返回根标签，False返回子标签
        """
        if value:
            return queryset.filter(parent__isnull=True)
        else:
            return queryset.filter(parent__isnull=False)


