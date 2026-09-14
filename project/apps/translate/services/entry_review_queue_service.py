# project/apps/translate/services/entry_review_queue_service.py
"""
用户级统一审核队列服务

每个用户维护一个全局唯一的审核队列（Redis list），仅保存
{file_id, uuid} 形式的顺序引用；条目内容真源仍在各文件的
parse_result:{file_id} 缓存中（由 ParseReviewService 管理）。
"""
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from django.core.cache import cache

from project.apps.translate.services.parse_review_service import ParseReviewService

logger = logging.getLogger(__name__)


class EntryReviewQueueService:
    """用户级统一审核队列服务"""

    CACHE_KEY_PREFIX = 'entry_review_queue'
    LOCK_KEY_PREFIX = 'entry_review_lock'
    DEFAULT_TTL = 25 * 3600

    @classmethod
    def _queue_key(cls, user_id: int) -> str:
        """生成用户审核队列的缓存键"""
        return f'{cls.CACHE_KEY_PREFIX}:{user_id}'

    @classmethod
    def _lock_key(cls, user_id: int) -> str:
        """生成用户审核队列锁的缓存键"""
        return f'{cls.LOCK_KEY_PREFIX}:{user_id}'

    # ------------------------------------------------------------------
    # 用户级锁（串行化多文件并发解析时的合并/去重）
    # ------------------------------------------------------------------
    @classmethod
    def acquire_lock(
        cls,
        user_id: int,
        timeout: int = 30,
        wait: float = 5.0,
        interval: float = 0.1,
    ) -> bool:
        """尝试获取用户级锁；成功返回 True，超时返回 False。

        Args:
            user_id: 用户 ID
            timeout: 锁的持有时间（秒）
            wait: 获取失败时的最长等待时间（秒）
            interval: 轮询重试间隔（秒）
        """
        key = cls._lock_key(user_id)
        token = uuid.uuid4().hex
        # cache.add 仅在键不存在时写入，天然具备原子性
        if cache.add(key, token, timeout=timeout):
            return True

        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            time.sleep(interval)
            if cache.add(key, token, timeout=timeout):
                return True
        return False

    @classmethod
    def release_lock(cls, user_id: int) -> None:
        """释放用户级锁（直接删除键，简单可靠）。"""
        cache.delete(cls._lock_key(user_id))

    @classmethod
    def _get_refs(cls, user_id: int) -> List[Dict[str, Any]]:
        """读取原始引用列表（不做有效性校验）"""
        refs = cache.get(cls._queue_key(user_id))
        if not refs:
            return []
        # 兼容缓存后端返回字符串的场景
        if isinstance(refs, str):
            try:
                refs = json.loads(refs)
            except json.JSONDecodeError:
                logger.error('解析条目审核队列缓存失败: %s', cls._queue_key(user_id))
                return []
        if not isinstance(refs, list):
            return []
        return refs

    @classmethod
    def _save_refs(
        cls,
        user_id: int,
        refs: List[Dict[str, Any]],
        timeout: Optional[int] = None,
    ) -> bool:
        """写回引用列表，默认刷新为 DEFAULT_TTL"""
        if timeout is None:
            timeout = cls.DEFAULT_TTL
        try:
            cache.set(cls._queue_key(user_id), refs, timeout=timeout)
            return True
        except Exception as e:
            logger.error('保存条目审核队列失败: %s, 错误: %s', cls._queue_key(user_id), str(e))
            return False

    @classmethod
    def list_refs(cls, user_id: int) -> List[Dict[str, Any]]:
        """返回有效引用；读取时顺带剔除缓存已过期的引用"""
        refs = cls._get_refs(user_id)
        valid_refs: List[Dict[str, Any]] = []
        for ref in refs:
            file_id = ref.get('file_id')
            if file_id is None or ref.get('uuid') is None:
                continue
            # 文件解析缓存已失效，说明该引用已不可审核，剔除
            if ParseReviewService.get_parse_result(file_id) is None:
                continue
            valid_refs.append(ref)
        if len(valid_refs) != len(refs):
            cls._save_refs(user_id, valid_refs)
        return valid_refs

    @classmethod
    def enqueue(cls, user_id: int, refs: List[Dict[str, Any]]) -> int:
        """把引用追加到队列，按 (file_id, uuid) 去重并保持顺序，返回新增数量"""
        existing = cls._get_refs(user_id)
        seen = {
            (ref.get('file_id'), ref.get('uuid'))
            for ref in existing
        }
        added = 0
        for ref in refs:
            file_id = ref.get('file_id')
            uuid = ref.get('uuid')
            if file_id is None or uuid is None:
                continue
            key = (file_id, uuid)
            if key in seen:
                continue
            existing.append({'file_id': file_id, 'uuid': uuid})
            seen.add(key)
            added += 1
        # 即使没有新增也写回，用于刷新 TTL
        cls._save_refs(user_id, existing)
        return added

    @classmethod
    def remove_file(cls, user_id: int, file_id: int) -> None:
        """移除指定文件的所有引用"""
        refs = cls._get_refs(user_id)
        remaining = [ref for ref in refs if ref.get('file_id') != file_id]
        if len(remaining) != len(refs):
            cls._save_refs(user_id, remaining)

    @classmethod
    def remove_entries(cls, user_id: int, refs: List[Dict[str, Any]]) -> None:
        """移除列表中指定的 (file_id, uuid) 引用"""
        keys = {
            (ref.get('file_id'), ref.get('uuid'))
            for ref in refs
        }
        existing = cls._get_refs(user_id)
        remaining = [
            ref for ref in existing
            if (ref.get('file_id'), ref.get('uuid')) not in keys
        ]
        if len(remaining) != len(existing):
            cls._save_refs(user_id, remaining)

    @classmethod
    def is_empty(cls, user_id: int) -> bool:
        """判断用户审核队列是否为空"""
        return len(cls.list_refs(user_id)) == 0

    @classmethod
    def clear(cls, user_id: int) -> None:
        """删除整个队列键"""
        cache.delete(cls._queue_key(user_id))

    @classmethod
    def earliest_expires_at(cls, user_id: int) -> Optional[float]:
        """返回队列中所有有效条目的最早审核截止时间，无有效引用返回 None"""
        expires_values: List[float] = []
        for ref in cls.list_refs(user_id):
            file_id = ref.get('file_id')
            cached_data = ParseReviewService.get_parse_result(file_id)
            if cached_data is None:
                continue
            expires_at = ParseReviewService.get_review_expires_at(cached_data, None)
            if expires_at is not None:
                expires_values.append(expires_at)
        if not expires_values:
            return None
        return min(expires_values)

    @classmethod
    def list_entries(cls, user_id: int) -> List[Dict[str, Any]]:
        """按队列顺序返回待审核条目列表（补充 file_id 与 file_name）"""
        from project.apps.translate.models import ParseFile

        entries: List[Dict[str, Any]] = []
        for ref in cls.list_refs(user_id):
            file_id = ref.get('file_id')
            uuid = ref.get('uuid')
            cached_data = ParseReviewService.get_parse_result_migrated(file_id)
            if cached_data is None:
                continue
            target = None
            for entry in cached_data.get('formatted_data') or []:
                if entry.get('uuid') == uuid:
                    target = entry
                    break
            if target is None:
                continue
            parse_file = (
                ParseFile.objects
                .filter(file_id=file_id)
                .select_related('file')
                .first()
            )
            file_name = parse_file.file.name if parse_file else None
            # 复制条目后再补充字段，避免污染 Redis 缓存中的条目结构
            item = dict(target)
            item['file_id'] = int(file_id)
            item['file_name'] = file_name
            entries.append(item)
        return entries

    # ------------------------------------------------------------------
    # 待办辅助方法
    # ------------------------------------------------------------------
    @classmethod
    def get_or_create_task(cls, user):
        """获取或创建该用户的全局唯一条目审核待办"""
        from django.contrib.contenttypes.models import ContentType
        from django.contrib.auth import get_user_model
        from project.apps.reconciliation.models import ScheduledTask

        content_type = ContentType.objects.get_for_model(get_user_model())
        task, _ = ScheduledTask.objects.get_or_create(
            content_type=content_type,
            object_id=user.id,
            task_type='entry_review',
            defaults={'scheduled_date': None, 'status': 'inactive'},
        )
        return task

    @classmethod
    def activate_task(cls, user):
        """激活待办（status='pending'）"""
        task = cls.get_or_create_task(user)
        task.status = 'pending'
        task.save()
        return task

    @classmethod
    def complete_task(cls, user) -> None:
        """完成待办（若存在）"""
        from django.contrib.contenttypes.models import ContentType
        from django.contrib.auth import get_user_model
        from project.apps.reconciliation.models import ScheduledTask

        content_type = ContentType.objects.get_for_model(get_user_model())
        task = ScheduledTask.objects.filter(
            content_type=content_type,
            object_id=user.id,
            task_type='entry_review',
        ).first()
        if task is not None:
            task.status = 'completed'
            task.save()

    @classmethod
    def deactivate_if_empty(cls, user) -> None:
        """队列为空时把待办置为未激活（若任务存在）"""
        if not cls.is_empty(user.id):
            return
        from django.contrib.contenttypes.models import ContentType
        from django.contrib.auth import get_user_model
        from project.apps.reconciliation.models import ScheduledTask

        content_type = ContentType.objects.get_for_model(get_user_model())
        task = ScheduledTask.objects.filter(
            content_type=content_type,
            object_id=user.id,
            task_type='entry_review',
        ).first()
        if task is not None:
            task.status = 'inactive'
            task.save()
