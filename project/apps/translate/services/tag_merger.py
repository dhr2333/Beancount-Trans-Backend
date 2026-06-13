"""
标签合并逻辑

用于合并来自不同来源的标签：
1. 原始标签（账单文件中的标签）
2. 映射标签（Expense/Assets/Income 映射关联的标签）
"""

from typing import Any, Dict, List, Optional, Tuple
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


def parse_source_tag_paths(source_tag: Optional[str]) -> List[str]:
    """从账单原始标签字符串解析 path 列表（不含 #）。"""
    if not source_tag:
        return []
    return [
        tag.strip().lstrip('#')
        for tag in source_tag.split()
        if tag.strip().startswith('#')
    ]


def merge_tags_with_details(
    source_tag: Optional[str],
    mapping_tag_sources: List[Dict[str, Any]],
    config: Optional[dict] = None,
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    合并标签并返回带来源信息的 tag_details。

    mapping_tag_sources 元素形如 {'tag': Tag, 'source': {'type': 'mapping', ...}}。
    """
    if config is None:
        config = {}

    details_map: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []

    def add_path(path: str, source: Dict[str, Any]) -> None:
        key = path.lower()
        if key not in details_map:
            details_map[key] = {'path': path, 'sources': []}
            order.append(key)
        sources = details_map[key]['sources']
        if source not in sources:
            sources.append(source)

    if config.get('keep_source', True) and source_tag:
        for path in parse_source_tag_paths(source_tag):
            add_path(path, {'type': 'source'})

    for item in mapping_tag_sources:
        tag_obj = item.get('tag')
        source = item.get('source') or {}
        if not tag_obj or not tag_obj.enable:
            continue
        path = get_tag_full_path(tag_obj)
        add_path(path, source)

    tag_details = [details_map[key] for key in order]
    if tag_details:
        separator = config.get('separator', ' ')
        formatted_tags = separator.join([f"#{d['path']}" for d in tag_details])
        return formatted_tags, tag_details
    return None, []


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
        all_tags.extend(parse_source_tag_paths(source_tag))

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


