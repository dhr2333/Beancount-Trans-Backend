# project/apps/translate/services/parse_review_service.py
"""
解析待办审核服务

封装解析结果的 Redis 缓存操作
"""
import json
import logging
from typing import Dict, List, Optional, Any
from django.core.cache import cache

logger = logging.getLogger(__name__)


class ParseReviewService:
    """解析结果缓存服务"""
    
    CACHE_KEY_PREFIX = 'parse_result'
    DEFAULT_TIMEOUT = 86400  # 24小时
    
    @classmethod
    def _get_cache_key(cls, file_id: int) -> str:
        """生成缓存键"""
        return f"{cls.CACHE_KEY_PREFIX}:{file_id}"
    
    @classmethod
    def get_parse_result(cls, file_id: int) -> Optional[Dict[str, Any]]:
        """从 Redis 获取解析结果
        
        Args:
            file_id: 文件ID
            
        Returns:
            解析结果字典，如果不存在则返回 None
        """
        cache_key = cls._get_cache_key(file_id)
        cached_data = cache.get(cache_key)
        
        if cached_data is None:
            return None
        
        # 如果缓存数据是字符串，需要解析 JSON
        if isinstance(cached_data, str):
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                logger.error(f"解析缓存数据失败: {cache_key}")
                return None
        
        return cached_data
    
    @classmethod
    def save_parse_result(cls, file_id: int, data: Dict[str, Any], timeout: int = None) -> bool:
        """保存解析结果到 Redis
        
        Args:
            file_id: 文件ID
            data: 解析结果数据，包含 formatted_data 等
            timeout: 过期时间（秒），默认24小时
            
        Returns:
            是否保存成功
        """
        if timeout is None:
            timeout = cls.DEFAULT_TIMEOUT
        
        cache_key = cls._get_cache_key(file_id)
        
        try:
            # 确保 formatted_data 中每条记录都有 edited_formatted
            if 'formatted_data' in data:
                for entry in data['formatted_data']:
                    if 'edited_formatted' not in entry:
                        # 初始状态时 edited_formatted 默认为 formatted
                        entry['edited_formatted'] = entry.get('formatted', '')
            
            cache.set(cache_key, data, timeout=timeout)
            logger.debug(f"保存解析结果到缓存: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"保存解析结果失败: {cache_key}, 错误: {str(e)}")
            return False
    
    @classmethod
    def update_entry_formatted(cls, file_id: int, uuid: str, formatted: str) -> bool:
        """更新单条记录的 formatted
        
        Args:
            file_id: 文件ID
            uuid: 条目UUID
            formatted: 新的格式化内容
            
        Returns:
            是否更新成功
        """
        cache_key = cls._get_cache_key(file_id)
        cached_data = cls.get_parse_result(file_id)
        
        if cached_data is None:
            logger.warning(f"缓存不存在，无法更新: {cache_key}")
            return False
        
        # 查找并更新对应的条目
        if 'formatted_data' in cached_data:
            for entry in cached_data['formatted_data']:
                if entry.get('uuid') == uuid:
                    entry['formatted'] = formatted
                    # 同时更新 edited_formatted（选择关键字会覆盖编辑内容）
                    entry['edited_formatted'] = formatted
                    break
            else:
                logger.warning(f"未找到UUID为 {uuid} 的条目")
                return False
        
        # 重新保存到缓存
        # 尝试获取剩余的过期时间，如果失败则使用默认值
        try:
            timeout = cache.ttl(cache_key)
            if timeout is None or timeout < 0:
                timeout = cls.DEFAULT_TIMEOUT
        except (AttributeError, TypeError):
            # RedisCache 后端可能不支持 ttl 方法，使用默认值
            timeout = cls.DEFAULT_TIMEOUT
        
        return cls.save_parse_result(file_id, cached_data, timeout=timeout)
    
    @classmethod
    def update_entry_edited_formatted(cls, file_id: int, uuid: str, edited_formatted: str) -> bool:
        """更新单条记录的 edited_formatted
        
        Args:
            file_id: 文件ID
            uuid: 条目UUID
            edited_formatted: 用户编辑后的内容
            
        Returns:
            是否更新成功
        """
        cache_key = cls._get_cache_key(file_id)
        cached_data = cls.get_parse_result(file_id)
        
        if cached_data is None:
            logger.warning(f"缓存不存在，无法更新: {cache_key}")
            return False
        
        # 查找并更新对应的条目
        if 'formatted_data' in cached_data:
            for entry in cached_data['formatted_data']:
                if entry.get('uuid') == uuid:
                    entry['edited_formatted'] = edited_formatted
                    break
            else:
                logger.warning(f"未找到UUID为 {uuid} 的条目")
                return False
        
        # 重新保存到缓存
        # 尝试获取剩余的过期时间，如果失败则使用默认值
        try:
            timeout = cache.ttl(cache_key)
            if timeout is None or timeout < 0:
                timeout = cls.DEFAULT_TIMEOUT
        except (AttributeError, TypeError):
            # RedisCache 后端可能不支持 ttl 方法，使用默认值
            timeout = cls.DEFAULT_TIMEOUT
        
        return cls.save_parse_result(file_id, cached_data, timeout=timeout)
    
    @classmethod
    def get_final_result(cls, file_id: int) -> Optional[List[Dict[str, Any]]]:
        """获取最终结果（使用 edited_formatted）
        
        Args:
            file_id: 文件ID
            
        Returns:
            最终结果列表，每个条目包含 edited_formatted
        """
        cached_data = cls.get_parse_result(file_id)
        
        if cached_data is None:
            return None
        
        formatted_data = cached_data.get('formatted_data', [])
        
        # 返回使用 edited_formatted 的结果
        result = []
        for entry in formatted_data:
            formatted_content = entry.get('edited_formatted', entry.get('formatted', ''))
            # 去除末尾的换行符（用于写入文件时连接）
            formatted_content = formatted_content.rstrip() if formatted_content else ''
            result.append({
                'uuid': entry.get('uuid'),
                'formatted': formatted_content,
                'selected_expense_key': entry.get('selected_expense_key'),
                'expense_candidates_with_score': entry.get('expense_candidates_with_score', []),
                'original_row': entry.get('original_row')
            })
        
        return result
    
    @classmethod
    def delete_parse_result(cls, file_id: int) -> bool:
        """删除解析结果缓存
        
        Args:
            file_id: 文件ID
            
        Returns:
            是否删除成功
        """
        cache_key = cls._get_cache_key(file_id)
        try:
            cache.delete(cache_key)
            logger.debug(f"删除解析结果缓存: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"删除解析结果缓存失败: {cache_key}, 错误: {str(e)}")
            return False

