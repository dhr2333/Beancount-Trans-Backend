"""
标签合并逻辑

用于合并来自不同来源的标签：
1. 原始标签（账单文件中的标签）
2. 映射标签（Expense/Assets/Income 映射关联的标签）
"""

from typing import List, Optional
from project.apps.tags.models import Tag


def get_tag_full_path(tag: Tag) -> str:
    """
    获取标签的完整路径
    
    Args:
        tag: Tag对象
    
    Returns:
        str: 标签完整路径，如 "Category/EDUCATION" 或 "Irregular"
    """
    return tag.get_full_path()


def merge_tags(
    source_tag: Optional[str],
    mapping_tags: List[Tag],
    config: Optional[dict] = None
) -> Optional[str]:
    """
    合并来自不同来源的标签
    
    Args:
        source_tag: 原始账单中的标签字符串，如 "#SourceTag1 #SourceTag2"
        mapping_tags: 映射关联的Tag对象列表
        config: 合并配置
            - deduplicate: bool 是否去重（默认True）
            - keep_source: bool 是否保留原始标签（默认True）
            - separator: str 标签分隔符（默认" "）
            - sort_alpha: bool 是否按字母排序（默认False，按优先级排序）
    
    Returns:
        str: 合并后的标签字符串，如 "#Tag1 #Tag2 #Tag3"，如果没有标签返回None
    """
    if config is None:
        config = {}
    
    all_tags = []
    
    # 1. 解析原始标签
    if config.get('keep_source', True) and source_tag:
        # 从字符串中提取标签名（去除#号和空格）
        source_tags_list = [
            tag.strip().lstrip('#')
            for tag in source_tag.split()
            if tag.strip().startswith('#')
        ]
        all_tags.extend(source_tags_list)
    
    # 2. 添加映射标签（包含层级结构）
    for tag_obj in mapping_tags:
        if tag_obj.enable:  # 只添加启用的标签
            tag_path = get_tag_full_path(tag_obj)
            all_tags.append(tag_path)
    
    # 3. 去重（保持顺序）
    if config.get('deduplicate', True):
        seen = set()
        unique_tags = []
        for tag in all_tags:
            tag_normalized = tag.lower()  # 不区分大小写去重
            if tag_normalized not in seen:
                seen.add(tag_normalized)
                unique_tags.append(tag)
        all_tags = unique_tags
    
    # 4. 排序（可选）
    if config.get('sort_alpha', False):
        all_tags.sort()
    
    # 5. 格式化为beancount标签格式
    if all_tags:
        separator = config.get('separator', ' ')
        formatted_tags = separator.join([f"#{tag}" for tag in all_tags])
        return formatted_tags
    
    return None


def get_mapping_tags(mapping_instance, enable_only: bool = True) -> List[Tag]:
    """
    从映射实例中获取关联的标签
    
    Args:
        mapping_instance: Expense/Assets/Income 映射实例
        enable_only: 是否只返回启用的标签
    
    Returns:
        List[Tag]: 标签对象列表
    """
    if not mapping_instance:
        return []
    
    try:
        tags = mapping_instance.tags.all()
        if enable_only:
            tags = tags.filter(enable=True)
        return list(tags)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"获取映射标签失败: {str(e)}")
        return []


def format_tags_for_beancount(tags: List[str]) -> str:
    """
    将标签列表格式化为beancount格式
    
    Args:
        tags: 标签名称列表，如 ["Category/EDUCATION", "Irregular"]
    
    Returns:
        str: 格式化的标签字符串，如 "#Category/EDUCATION #Irregular"
    """
    if not tags:
        return ""
    
    return " ".join([f"#{tag}" for tag in tags])


