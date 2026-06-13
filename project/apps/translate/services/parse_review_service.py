# project/apps/translate/services/parse_review_service.py
"""
解析待办审核服务

封装解析结果的 Redis 缓存操作
"""
import hashlib
import json
import logging
import re
import time
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from django.core.cache import cache

if TYPE_CHECKING:
    from project.apps.reconciliation.models import ScheduledTask

logger = logging.getLogger(__name__)

TAG_TOKEN_RE = re.compile(r'#\S+')


class ParseReviewService:
    """解析结果缓存服务"""
    
    CACHE_KEY_PREFIX = 'parse_result'
    REVIEW_DEADLINE_SECONDS = 24 * 3600  # 用户审核截止（对外）
    # 须长于 REVIEW_DEADLINE 及 Celery Beat 调度间隔，避免到期自动写入时缓存已失效
    DEFAULT_CACHE_TIMEOUT = 25 * 3600  # Redis TTL（对内）

    @classmethod
    def default_tag_overrides(cls) -> Dict[str, List[str]]:
        return {'removed_paths': [], 'added_paths': []}

    @classmethod
    def normalize_entry_tag_fields(cls, entry: Dict[str, Any]) -> None:
        """补齐条目 tag 相关字段。"""
        if 'tag_details' not in entry or entry['tag_details'] is None:
            entry['tag_details'] = []
        if 'tag_overrides' not in entry or entry['tag_overrides'] is None:
            entry['tag_overrides'] = cls.default_tag_overrides()
        else:
            overrides = entry['tag_overrides']
            overrides.setdefault('removed_paths', [])
            overrides.setdefault('added_paths', [])

    @classmethod
    def apply_tag_overrides(
        cls,
        tag_details: List[Dict[str, Any]],
        tag_overrides: Optional[Dict[str, List[str]]],
    ) -> List[Dict[str, Any]]:
        """根据用户覆盖生成有效 tag_details。"""
        overrides = tag_overrides or cls.default_tag_overrides()
        removed = {path.lower() for path in overrides.get('removed_paths', [])}
        added_paths = overrides.get('added_paths', [])

        filtered = [
            detail for detail in (tag_details or [])
            if detail.get('path', '').lower() not in removed
        ]
        existing = {detail.get('path', '').lower() for detail in filtered}
        for path in added_paths:
            if path.lower() in existing:
                continue
            filtered.append({'path': path, 'sources': [{'type': 'manual'}]})
            existing.add(path.lower())
        return filtered

    @classmethod
    def set_header_tags(cls, formatted: str, tag_paths: List[str]) -> str:
        """将首行标签替换为 tag_paths 对应的 #path 列表。"""
        if not formatted:
            return formatted
        lines = formatted.split('\n')
        first_line = TAG_TOKEN_RE.sub('', lines[0]).rstrip()
        if tag_paths:
            tag_str = ' '.join(f'#{path}' for path in tag_paths)
            lines[0] = f'{first_line} {tag_str}'.rstrip()
        else:
            lines[0] = first_line
        return '\n'.join(lines)

    @classmethod
    def rebuild_entry_edited_formatted(cls, entry: Dict[str, Any]) -> str:
        """根据 formatted 与 tag 覆盖重建 edited_formatted。"""
        cls.normalize_entry_tag_fields(entry)
        effective_details = cls.apply_tag_overrides(
            entry.get('tag_details', []),
            entry.get('tag_overrides'),
        )
        tag_paths = [detail['path'] for detail in effective_details if detail.get('path')]
        base_formatted = entry.get('formatted') or entry.get('edited_formatted') or ''
        edited = cls.set_header_tags(base_formatted, tag_paths)
        entry['edited_formatted'] = edited
        return edited

    @classmethod
    def get_effective_tag_details(cls, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        cls.normalize_entry_tag_fields(entry)
        return cls.apply_tag_overrides(
            entry.get('tag_details', []),
            entry.get('tag_overrides'),
        )

    @classmethod
    def entry_response_payload(cls, entry: Dict[str, Any]) -> Dict[str, Any]:
        """构造单条条目的 tag 相关 API 字段。"""
        cls.normalize_entry_tag_fields(entry)
        return {
            'tag_details': cls.get_effective_tag_details(entry),
            'tag_overrides': entry.get('tag_overrides', cls.default_tag_overrides()),
        }

    @classmethod
    def _entry_header_has_tags(cls, entry: Dict[str, Any]) -> bool:
        formatted = entry.get('formatted') or entry.get('edited_formatted') or ''
        first_line = formatted.split('\n')[0] if formatted else ''
        return bool(TAG_TOKEN_RE.search(first_line))

    @classmethod
    def ensure_entry_tag_details(
        cls,
        entry: Dict[str, Any],
        owner_id: int,
        config,
        user=None,
    ) -> bool:
        """缺少 tag_details 时根据 original_row 重算来源（兼容历史缓存）。"""
        cls.normalize_entry_tag_fields(entry)
        if entry.get('tag_details'):
            return False
        if not cls._entry_header_has_tags(entry):
            return False
        original_row = entry.get('original_row')
        if not original_row:
            return False

        selected_key = entry.get('selected_expense_key') or None
        if selected_key == '':
            selected_key = None

        from project.apps.translate.services.parse.transaction_parser import single_parse_transaction
        from project.apps.translate.services.alipay_refund_peer import resolve_refund_peer_for_row

        try:
            refund_peer = resolve_refund_peer_for_row(
                original_row,
                user,
                owner_id,
                config,
                selected_key,
            )
            parsed = single_parse_transaction(
                original_row,
                owner_id,
                config,
                selected_key,
                refund_peer=refund_peer,
            )
        except Exception as exc:
            logger.warning('回填 tag_details 失败: %s', exc)
            return False

        tag_details = parsed.get('tag_details') or []
        if not tag_details:
            return False

        entry['tag_details'] = tag_details
        cls.rebuild_entry_edited_formatted(entry)
        return True

    @classmethod
    def backfill_tag_details_in_data(
        cls,
        cached_data: Dict[str, Any],
        owner_id: int,
        config,
        user=None,
    ) -> bool:
        """为缓存中缺失 tag_details 的条目批量回填。"""
        changed = False
        for entry in cached_data.get('formatted_data') or []:
            if cls.ensure_entry_tag_details(entry, owner_id, config, user=user):
                changed = True
        return changed

    @classmethod
    def get_review_expires_at(
        cls,
        cached_data: Optional[Dict[str, Any]],
        task: Optional['ScheduledTask'] = None,
    ) -> Optional[float]:
        """获取用户审核截止时间（Unix 时间戳，秒）。"""
        if cached_data:
            review_expires_at = cached_data.get('review_expires_at')
            if review_expires_at is not None:
                return float(review_expires_at)
            created_at = cached_data.get('created_at')
            if created_at is not None:
                return float(created_at) + cls.REVIEW_DEADLINE_SECONDS
        if task is not None and task.created is not None:
            return task.created.timestamp() + cls.REVIEW_DEADLINE_SECONDS
        return None

    @classmethod
    def is_review_expired(
        cls,
        cached_data: Optional[Dict[str, Any]],
        task: Optional['ScheduledTask'] = None,
        now: Optional[float] = None,
    ) -> bool:
        """判断解析待办是否已过用户审核截止时间。"""
        expires_at = cls.get_review_expires_at(cached_data, task)
        if expires_at is None:
            return False
        if now is None:
            now = time.time()
        return now >= expires_at
    
    @classmethod
    def _get_cache_key(cls, file_id: int) -> str:
        """生成缓存键"""
        return f"{cls.CACHE_KEY_PREFIX}:{file_id}"

    @classmethod
    def _ttl_for_resave(cls, file_id: int) -> int:
        cache_key = cls._get_cache_key(file_id)
        try:
            timeout = cache.ttl(cache_key)
            if timeout is None or timeout < 0:
                timeout = cls.DEFAULT_CACHE_TIMEOUT
        except (AttributeError, TypeError):
            timeout = cls.DEFAULT_CACHE_TIMEOUT
        return timeout

    @classmethod
    def normalize_stale_entry_uuids(cls, cached_data: Dict[str, Any]) -> bool:
        """历史数据：uuid 为 null 时，用与 ParseStep 一致的 md5(original_row) 补齐，便于审核页 PUT 能匹配条目。"""
        changed = False
        for entry in cached_data.get("formatted_data") or []:
            if entry.get("uuid"):
                continue
            row = entry.get("original_row")
            if row is None:
                continue
            entry["uuid"] = hashlib.md5(str(row).encode()).hexdigest()
            changed = True
        return changed

    @classmethod
    def get_parse_result_migrated(cls, file_id: int) -> Optional[Dict[str, Any]]:
        """读取解析缓存；若存在 uuid 为空的条目则就地补齐并写回 Redis。"""
        data = cls.get_parse_result(file_id)
        if data is None:
            return None
        if cls.normalize_stale_entry_uuids(data):
            cls.save_parse_result(file_id, data, timeout=cls._ttl_for_resave(file_id))
        return data
    
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
            timeout: Redis 缓存 TTL（秒），默认见 DEFAULT_CACHE_TIMEOUT
            
        Returns:
            是否保存成功
        """
        if timeout is None:
            timeout = cls.DEFAULT_CACHE_TIMEOUT
        
        cache_key = cls._get_cache_key(file_id)
        
        try:
            # 确保 formatted_data 中每条记录都有 edited_formatted
            if 'formatted_data' in data:
                for entry in data['formatted_data']:
                    cls.normalize_entry_tag_fields(entry)
                    if 'edited_formatted' not in entry:
                        entry['edited_formatted'] = entry.get('formatted', '')
            
            cache.set(cache_key, data, timeout=timeout)
            logger.debug(f"保存解析结果到缓存: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"保存解析结果失败: {cache_key}, 错误: {str(e)}")
            return False
    
    @classmethod
    def update_entry_formatted(
        cls,
        file_id: int,
        uuid: str,
        formatted: str,
        tag_details: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """更新单条记录的 formatted（重解析时使用，保留 tag_overrides）。"""
        cache_key = cls._get_cache_key(file_id)
        cached_data = cls.get_parse_result_migrated(file_id)

        if cached_data is None:
            logger.warning(f"缓存不存在，无法更新: {cache_key}")
            return False

        if 'formatted_data' in cached_data:
            for entry in cached_data['formatted_data']:
                if entry.get('uuid') == uuid:
                    entry['formatted'] = formatted
                    if tag_details is not None:
                        entry['tag_details'] = tag_details
                    cls.normalize_entry_tag_fields(entry)
                    cls.rebuild_entry_edited_formatted(entry)
                    break
            else:
                logger.warning(f"未找到UUID为 {uuid} 的条目")
                return False

        timeout = cls._ttl_for_resave(file_id)
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
        cached_data = cls.get_parse_result_migrated(file_id)
        
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
        
        timeout = cls._ttl_for_resave(file_id)
        return cls.save_parse_result(file_id, cached_data, timeout=timeout)

    @classmethod
    def update_entry_tags(
        cls,
        file_id: int,
        uuid: str,
        action: str,
        tag_path: str,
    ) -> Optional[Dict[str, Any]]:
        """添加或移除条目标签，返回更新后的条目快照。"""
        cached_data = cls.get_parse_result_migrated(file_id)
        if cached_data is None:
            return None

        tag_path = (tag_path or '').strip().lstrip('#')
        if not tag_path:
            return None
        if action not in ('add', 'remove'):
            return None

        target_entry = None
        for entry in cached_data.get('formatted_data', []):
            if entry.get('uuid') == uuid:
                target_entry = entry
                break
        if target_entry is None:
            return None

        cls.normalize_entry_tag_fields(target_entry)
        overrides = target_entry['tag_overrides']
        removed_paths = overrides['removed_paths']
        added_paths = overrides['added_paths']
        path_lower = tag_path.lower()

        if action == 'remove':
            if not any(p.lower() == path_lower for p in removed_paths):
                removed_paths.append(tag_path)
            overrides['added_paths'] = [p for p in added_paths if p.lower() != path_lower]
        else:
            overrides['removed_paths'] = [p for p in removed_paths if p.lower() != path_lower]
            if not any(p.lower() == path_lower for p in added_paths):
                added_paths.append(tag_path)

        edited = cls.rebuild_entry_edited_formatted(target_entry)
        timeout = cls._ttl_for_resave(file_id)
        if not cls.save_parse_result(file_id, cached_data, timeout=timeout):
            return None

        return {
            'uuid': uuid,
            'edited_formatted': edited.rstrip() if edited else '',
            **cls.entry_response_payload(target_entry),
        }

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

