# project/apps/translate/services/parse/ignore_registry.py
from typing import Dict, Callable, Optional

class IgnoreRuleRegistry:
    def __init__(self):
        self.pre_filters: Dict[str, Callable] = {}  # 解析前过滤
        self.post_filters: Dict[str, Callable] = {}  # 解析后过滤
    
    def register_pre_filter(self, bill_type: str, rule: Callable[[Dict], bool]):
        """注册预过滤规则"""
        self.pre_filters[bill_type] = rule
        
    def register_post_filter(self, bill_type: str, rule: Callable[[Dict], bool]):
        """注册后过滤规则"""
        self.post_filters[bill_type] = rule
        
    def get_pre_filter(self, bill_type: str) -> Optional[Callable]:
        """获取预过滤规则"""
        return self.pre_filters.get(bill_type)
    
    def get_post_filter(self, bill_type: str) -> Optional[Callable]:
        """获取后过滤规则"""
        return self.post_filters.get(bill_type)

# 全局注册表实例
registry = IgnoreRuleRegistry()
