# project/apps/translate/services/parse/ignore_registry.py
from typing import Dict, Callable, Optional

class IgnoreRuleRegistry:
    def __init__(self):
        self.pre_filters: Dict[str, Callable] = {}  # 解析前过滤
        self.post_filters: Dict[str, Callable] = {}  # 解析后过滤
        self.pre_universal_filters = []  # 通用预过滤规则
        self.post_universal_filters = []  # 通用后过滤规则
    
    def register_pre_filter(self, bill_type: str, rule: Callable[[Dict], bool]):
        """注册预过滤规则"""
        if bill_type not in self.pre_filters:
            self.pre_filters[bill_type] = []
        self.pre_filters[bill_type].append(rule)
        
    def register_post_filter(self, bill_type: str, rule: Callable[[Dict], bool]):
        """注册后过滤规则"""
        if bill_type not in self.post_filters:
            self.post_filters[bill_type] = []
        self.post_filters[bill_type].append(rule)

    def register_pre_universal_filter(self, rule: Callable[[Dict], bool]):
        """注册通用预过滤规则"""
        self.pre_universal_filters.append(rule)    

    def register_post_universal_filter(self, rule: Callable[[Dict], bool]):
        """注册通用后过滤规则"""
        self.post_universal_filters.append(rule)
    
    def get_pre_filter(self, bill_type: str) -> Optional[Callable]:
        """获取预过滤规则"""
        return self.pre_filters.get(bill_type, [])
    
    def get_post_filter(self, bill_type: str) -> Optional[Callable]:
        """获取后过滤规则"""
        return self.post_filters.get(bill_type, [])

    def get_pre_universal_filters(self) -> list:
        """获取通用预过滤规则"""
        return self.pre_universal_filters
    
    def get_post_universal_filters(self) -> list:
        """获取通用后过滤规则"""
        return self.post_universal_filters
    
# 全局注册表实例
registry = IgnoreRuleRegistry()

def post_empty_filter(entry, args):
    """通用空数据过滤"""
    return entry == {}

registry.register_post_universal_filter(post_empty_filter)