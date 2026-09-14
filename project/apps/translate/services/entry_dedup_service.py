# project/apps/translate/services/entry_dedup_service.py
"""
条目审核去重服务

多张账单合并解析为统一条目审核待办时，同一笔交易可能重复出现。
本服务在条目入队前做去重：
1. 先用确定性规则（交易单号 / 日期 + 金额）筛出候选；
2. 再由 LLM 判定候选对是否真为同一笔交易；
3. LLM 不可用或失败时，回退到日期 + 金额 + 类型 + 对方 + 品名的精确匹配。

本服务与队列服务解耦：existing_entries 由调用方传入。
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)

# LLM 返回 JSON 数组时的宽松提取（容忍 ```json 代码块或前后解释文字）
_JSON_ARRAY_PATTERN = re.compile(r'\[.*\]', re.DOTALL)


class EntryDedupService:
    """跨账单条目去重服务（全 classmethod）"""

    @classmethod
    def is_enabled(cls) -> bool:
        """去重开关，默认开启。"""
        return bool(getattr(settings, 'ENTRY_REVIEW_DEDUP_ENABLED', True))

    # ------------------------------------------------------------------
    # 取值辅助
    # ------------------------------------------------------------------
    @classmethod
    def entry_date(cls, entry: Dict[str, Any]) -> Optional[str]:
        """条目日期：优先原始行 transaction_time 前 10 位，否则用解析条目的 date。"""
        original_row = entry.get('original_row') or {}
        transaction_time = original_row.get('transaction_time')
        if transaction_time:
            text = str(transaction_time).strip()
            if text:
                return text[:10]
        date = entry.get('date')
        if date:
            text = str(date).strip()
            if text:
                return text
        return None

    @classmethod
    def entry_amount(cls, entry: Dict[str, Any]) -> Optional[float]:
        """条目金额：优先原始行 amount，否则用解析条目 amount；无法转 float 返回 None。"""
        original_row = entry.get('original_row') or {}
        raw = original_row.get('amount')
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            raw = entry.get('amount')
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    @classmethod
    def entry_order_uuid(cls, entry: Dict[str, Any]) -> str:
        """条目对应的交易单号（支付宝/微信有，银行账单通常没有）。"""
        original_row = entry.get('original_row') or {}
        return str(original_row.get('uuid') or '').strip()

    @classmethod
    def entry_tx_type(cls, entry: Dict[str, Any]) -> str:
        """收支方向字符串。"""
        original_row = entry.get('original_row') or {}
        return str(original_row.get('transaction_type') or '').strip()

    @classmethod
    def entry_counterparty(cls, entry: Dict[str, Any]) -> str:
        """交易对方字符串。"""
        original_row = entry.get('original_row') or {}
        return str(original_row.get('counterparty') or '').strip()

    @classmethod
    def entry_commodity(cls, entry: Dict[str, Any]) -> str:
        """商品说明字符串。"""
        original_row = entry.get('original_row') or {}
        return str(original_row.get('commodity') or '').strip()

    @classmethod
    def entry_file_label(cls, entry: Dict[str, Any]) -> str:
        """条目来源文件标识（仅用于日志，可能不存在）。"""
        for key in ('file_name', 'file_id', 'source_file', 'bill_identifier'):
            value = entry.get(key)
            if value:
                return str(value)
        return ''

    # ------------------------------------------------------------------
    # 确定性判定
    # ------------------------------------------------------------------
    @classmethod
    def _is_fast_duplicate(cls, new_entry: Dict[str, Any], existing_entry: Dict[str, Any]) -> bool:
        """快速判定：两条交易单号均非空且相同，且日期相同。"""
        new_uuid = cls.entry_order_uuid(new_entry)
        existing_uuid = cls.entry_order_uuid(existing_entry)
        if not new_uuid or not existing_uuid or new_uuid != existing_uuid:
            return False
        new_date = cls.entry_date(new_entry)
        existing_date = cls.entry_date(existing_entry)
        return bool(new_date) and new_date == existing_date

    @classmethod
    def _is_candidate(cls, new_entry: Dict[str, Any], existing_entry: Dict[str, Any]) -> bool:
        """候选筛选：日期相同且金额差值在容差内。"""
        new_date = cls.entry_date(new_entry)
        existing_date = cls.entry_date(existing_entry)
        if not new_date or not existing_date or new_date != existing_date:
            return False

        new_amount = cls.entry_amount(new_entry)
        existing_amount = cls.entry_amount(existing_entry)
        if new_amount is None or existing_amount is None:
            return False

        tolerance = float(getattr(settings, 'ENTRY_REVIEW_DEDUP_AMOUNT_TOLERANCE', 1.00))
        return abs(new_amount - existing_amount) <= tolerance

    @classmethod
    def _is_exact_duplicate(cls, new_entry: Dict[str, Any], existing_entry: Dict[str, Any]) -> bool:
        """确定性精确匹配（LLM 不可用时的回退判定）。"""
        new_date = cls.entry_date(new_entry)
        existing_date = cls.entry_date(existing_entry)
        if not new_date or not existing_date or new_date != existing_date:
            return False

        new_amount = cls.entry_amount(new_entry)
        existing_amount = cls.entry_amount(existing_entry)
        if new_amount is None or existing_amount is None or new_amount != existing_amount:
            return False

        return (
            cls.entry_tx_type(new_entry) == cls.entry_tx_type(existing_entry)
            and cls.entry_counterparty(new_entry) == cls.entry_counterparty(existing_entry)
            and cls.entry_commodity(new_entry) == cls.entry_commodity(existing_entry)
        )

    # ------------------------------------------------------------------
    # LLM 判定
    # ------------------------------------------------------------------
    @classmethod
    def _pair_summary(cls, pair: Tuple[Dict[str, Any], Dict[str, Any]], index: int) -> str:
        """把一对候选条目压缩为编号摘要文本，供 LLM 判断。"""
        new_entry, existing_entry = pair

        def _one(label: str, entry: Dict[str, Any]) -> str:
            formatted = entry.get('edited_formatted') or entry.get('formatted') or ''
            formatted_one_line = ' '.join(str(formatted).split())
            return (
                f"{label}: 日期={cls.entry_date(entry) or '未知'}；"
                f"金额={cls.entry_amount(entry)}；"
                f"收支={cls.entry_tx_type(entry) or '未知'}；"
                f"对方={cls.entry_counterparty(entry)}；"
                f"商品={cls.entry_commodity(entry)}；"
                f"账目文本={formatted_one_line}"
            )

        return f"{index}. {_one('新条目', new_entry)}\n   {_one('已存在条目', existing_entry)}"

    @classmethod
    def _build_judge_prompt(cls, pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]]) -> str:
        """构造 LLM 判定 prompt。"""
        lines = [
            '下面是若干「新条目 / 已存在条目」的候选对。',
            '请判断每一对是否描述的是同一笔交易（日期、金额、对方、商品等一致，或明显为跨账单重复记录的同一笔）。',
            '只返回一个 JSON 数组，元素为 true 或 false，顺序与输入编号一致，不要输出任何解释文字。',
            '',
        ]
        for index, pair in enumerate(pairs, start=1):
            lines.append(cls._pair_summary(pair, index))
        return '\n'.join(lines)

    @classmethod
    def _parse_verdicts(cls, content: str, expected: int) -> Optional[List[bool]]:
        """从模型返回内容中解析布尔数组。"""
        if not content:
            return None
        text = content.strip()
        if text.startswith('```'):
            text = text.strip('`').strip()
            if text.lower().startswith('json'):
                text = text[4:].strip()

        data = None
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            match = _JSON_ARRAY_PATTERN.search(text)
            if match:
                try:
                    data = json.loads(match.group(0))
                except (ValueError, TypeError):
                    data = None

        if not isinstance(data, list) or len(data) != expected:
            return None

        verdicts: List[bool] = []
        for item in data:
            if isinstance(item, bool):
                verdicts.append(item)
            elif isinstance(item, (int, float)):
                verdicts.append(bool(item))
            elif isinstance(item, str):
                verdicts.append(item.strip().lower() in ('true', '1', 'yes', '是', '重复'))
            else:
                return None
        return verdicts

    @classmethod
    def _llm_judge_pairs(
        cls,
        user,
        pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]],
    ) -> Optional[List[bool]]:
        """调用 LLM 批量判定候选对；不可用或异常时返回 None。"""
        if not pairs:
            return None

        from project.apps.assistant.services.api_key_resolver import resolve_llm_provider

        try:
            provider = resolve_llm_provider(user)
        except Exception as exc:
            logger.warning('条目去重解析 LLM 供给失败: %s', exc)
            return None
        if not provider.configured:
            return None

        try:
            from openai import OpenAI

            timeout = float(getattr(settings, 'ENTRY_REVIEW_DEDUP_LLM_TIMEOUT', 15))
            client = OpenAI(
                api_key=provider.api_key,
                base_url=provider.base_url,
                timeout=timeout,
            )
            response = client.chat.completions.create(
                model=provider.model,
                messages=[{'role': 'user', 'content': cls._build_judge_prompt(pairs)}],
                temperature=0,
            )
            content = (response.choices[0].message.content or '').strip()
            verdicts = cls._parse_verdicts(content, len(pairs))
            if verdicts is None:
                logger.warning('条目去重 LLM 返回无法解析，长度不匹配或非 JSON 数组')
            return verdicts
        except Exception as exc:
            logger.warning('条目去重 LLM 判定失败，将回退精确匹配: %s', exc)
            return None

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------
    @classmethod
    def dedup_new_entries(
        cls,
        user,
        new_entries: List[Dict[str, Any]],
        existing_entries: Optional[List[Dict[str, Any]]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """对新增条目去重。

        Args:
            user: 当前用户（用于解析 LLM 供给）。
            new_entries: 待入队的新条目列表。
            existing_entries: 已入队/已存在的条目列表，由调用方提供。

        Returns:
            (kept, duplicates)：kept 为保留的新条目，duplicates 为判为重复的新条目，均保持原顺序。
        """
        if not cls.is_enabled() or not new_entries or not existing_entries:
            return (list(new_entries), [])

        duplicate_flags = [False] * len(new_entries)

        # 第一步：确定性快速判定（交易单号一致）
        pending_indices: List[int] = []
        for index, entry in enumerate(new_entries):
            if any(cls._is_fast_duplicate(entry, existing) for existing in existing_entries):
                duplicate_flags[index] = True
            else:
                pending_indices.append(index)

        # 第二步：筛出候选对，交 LLM 判定
        pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        pair_pending_pos: List[int] = []
        for pos, index in enumerate(pending_indices):
            entry = new_entries[index]
            for existing in existing_entries:
                if cls._is_candidate(entry, existing):
                    pairs.append((entry, existing))
                    pair_pending_pos.append(pos)

        if pairs:
            verdicts = cls._llm_judge_pairs(user, pairs)
            if verdicts is not None:
                for pos, verdict in zip(pair_pending_pos, verdicts):
                    if verdict:
                        duplicate_flags[pending_indices[pos]] = True
            else:
                # LLM 不可用/失败：回退确定性精确匹配
                for index in pending_indices:
                    entry = new_entries[index]
                    if any(cls._is_exact_duplicate(entry, existing) for existing in existing_entries):
                        duplicate_flags[index] = True

        kept = [entry for index, entry in enumerate(new_entries) if not duplicate_flags[index]]
        duplicates = [entry for index, entry in enumerate(new_entries) if duplicate_flags[index]]

        if duplicates:
            logger.info(
                '条目去重: 新条目 %d 条，保留 %d 条，剔除 %d 条',
                len(new_entries),
                len(kept),
                len(duplicates),
            )
            for entry in duplicates:
                logger.info('条目去重剔除: %s', cls.describe_duplicate(entry))
        return (kept, duplicates)

    @classmethod
    def describe_duplicate(
        cls,
        entry: Dict[str, Any],
        existing_entry: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """生成条目摘要（仅用于日志排查）。"""
        summary = {
            'uuid': entry.get('uuid'),
            'date': cls.entry_date(entry),
            'amount': cls.entry_amount(entry),
            'order_uuid': cls.entry_order_uuid(entry),
            'tx_type': cls.entry_tx_type(entry),
            'counterparty': cls.entry_counterparty(entry),
            'file': cls.entry_file_label(entry),
        }
        if existing_entry is not None:
            summary['matched'] = {
                'uuid': existing_entry.get('uuid'),
                'date': cls.entry_date(existing_entry),
                'amount': cls.entry_amount(existing_entry),
                'order_uuid': cls.entry_order_uuid(existing_entry),
                'file': cls.entry_file_label(existing_entry),
            }
        return summary
