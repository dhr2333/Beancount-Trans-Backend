# project/apps/translate/services/recurring_bookkeeping_service.py
"""
循环待办：把「固定模板」并入用户统一审核队列

到期时把循环待办（RecurringTask, kind='generate_review'）的模板正文**原样**
写入用户级暂存区（复用 ParseReviewService，缓存键 ``parse_result:recurring:{user_id}``），
再并入统一审核队列并激活 entry_review 待办。

本服务不写任何账本文件，条目写入交由审核确认链路；条目**永不过期、不自动写入**
（``review_expires_at=None``），语法错误留待确认写入时由现有链路报出。
"""
import logging
import time
import uuid as uuid_lib
from datetime import date
from typing import Any, Dict, List, Optional

from django.conf import settings

from project.apps.translate.services.entry_review_queue_service import (
    EntryReviewQueueService,
)
from project.apps.translate.services.parse_review_service import ParseReviewService

logger = logging.getLogger(__name__)

# 未确认的循环待审核条目保留时长（秒），默认 90 天
DEFAULT_TTL = 90 * 24 * 3600


class RecurringBookkeepingService:
    """循环待办模板暂存区服务（全 classmethod）"""

    SOURCE = 'recurring'
    SOURCE_LABEL = '循环待办'

    # ------------------------------------------------------------------
    # 暂存区基础读写（缓存键 parse_result:recurring:{user_id}）
    # ------------------------------------------------------------------
    @classmethod
    def ttl(cls) -> int:
        """暂存区 TTL（秒）"""
        return int(getattr(settings, 'RECURRING_REVIEW_TTL', DEFAULT_TTL))

    @classmethod
    def staging_key(cls, user_id) -> str:
        """暂存区标识，作为 ParseReviewService 的 file_id 参数使用。"""
        return f'{cls.SOURCE}:{user_id}'

    @classmethod
    def get_staging_data(cls, user_id) -> Optional[Dict[str, Any]]:
        """读取暂存区原始数据（不存在返回 None）。"""
        return ParseReviewService.get_parse_result(cls.staging_key(user_id))

    @classmethod
    def has_staging(cls, user_id) -> bool:
        """用户是否存在循环待办暂存区。"""
        return cls.get_staging_data(user_id) is not None

    @classmethod
    def touch(cls, user_id) -> None:
        """读取时续期暂存区 TTL。"""
        data = cls.get_staging_data(user_id)
        if data is not None:
            ParseReviewService.save_parse_result(
                cls.staging_key(user_id), data, timeout=cls.ttl()
            )

    @classmethod
    def clear(cls, user_id) -> bool:
        """删除整个暂存区。"""
        return ParseReviewService.delete_parse_result(cls.staging_key(user_id))

    @classmethod
    def source_ref(cls, entry_uuid: str) -> Dict[str, Any]:
        """统一审核队列引用（循环来源没有 file_id）。"""
        return {'source': cls.SOURCE, 'file_id': None, 'uuid': entry_uuid}

    @classmethod
    def _staging_entries(cls, user_id) -> List[Dict[str, Any]]:
        data = cls.get_staging_data(user_id) or {}
        return data.get('formatted_data') or []

    @classmethod
    def list_entries(cls, user_id) -> List[Dict[str, Any]]:
        """按暂存区顺序返回条目副本，并补充来源字段。"""
        entries: List[Dict[str, Any]] = []
        for entry in cls._staging_entries(user_id):
            item = dict(entry)
            item['source'] = cls.SOURCE
            item['file_id'] = None
            item['file_name'] = item.get('file_name') or cls.SOURCE_LABEL
            entries.append(item)
        return entries

    @classmethod
    def get_entry(cls, user_id, entry_uuid: str) -> Optional[Dict[str, Any]]:
        """按 uuid 取单条条目（副本）。"""
        for entry in cls.list_entries(user_id):
            if entry.get('uuid') == entry_uuid:
                return entry
        return None

    # ------------------------------------------------------------------
    # 条目构建与入队
    # ------------------------------------------------------------------
    @classmethod
    def build_entry(cls, defn, due_date: date) -> Dict[str, Any]:
        """把定义模板原样包装成审核条目（无占位符、无替换、不校验语法）。"""
        from project.apps.reconciliation.services import RecurringTaskService

        text = (defn.template or '').rstrip()
        return {
            'uuid': uuid_lib.uuid4().hex,
            'formatted': text,
            'edited_formatted': text,
            'selected_expense_key': None,
            'expense_candidates_with_score': [],
            'installment_role': None,
            'installment_period': None,
            'tag_details': [],
            'tag_overrides': ParseReviewService.default_tag_overrides(),
            'file_name': RecurringTaskService.label(defn),
            # 仅作元数据，不改写模板正文中的日期
            'date': due_date.isoformat(),
        }

    @classmethod
    def _append_to_staging(cls, user_id, entries: List[Dict[str, Any]]) -> bool:
        """把条目追加到暂存区（review_expires_at 恒为 None，永不自动写入）。"""
        data = cls.get_staging_data(user_id)
        if data is None:
            data = {
                'formatted_data': [],
                'created_at': time.time(),
                'review_expires_at': None,
            }
        data.setdefault('formatted_data', [])
        data['formatted_data'].extend(entries)
        return ParseReviewService.save_parse_result(
            cls.staging_key(user_id), data, timeout=cls.ttl()
        )

    @classmethod
    def generate_for_definition(cls, user, defn, due_date: date) -> bool:
        """把定义模板并入暂存区与统一审核队列，并激活入口审核待办。"""
        entry = cls.build_entry(defn, due_date)
        cls._append_to_staging(user.id, [entry])
        EntryReviewQueueService.enqueue(user.id, [cls.source_ref(entry['uuid'])])
        EntryReviewQueueService.activate_task(user)
        return True
