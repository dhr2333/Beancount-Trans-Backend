"""校验助手回复中的金额是否来自 BQL 查询结果。"""
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Protocol

_AMOUNT_PATTERN = re.compile(
    r'(?<![\d.])(-?\d{1,3}(?:,\d{3})+|-?\d+)(?:\.(\d{1,2}))?(?![\d.])',
)
_TOTAL_KEYWORD_PATTERN = re.compile(r'共计|合计|总计|加起来|总和|一共')
_NORMALIZED_ZERO = re.compile(r'\b0\.00\s+[A-Z]{3}\b')
_AMOUNT_SUFFIX = re.compile(r'\d+(?:\.\d+)?\s*[A-Z]{3}\s*$')

GUARD_RETRY_MESSAGE = (
    '你的回答含有查询结果中未出现的金额或存在手动计算。'
    '请仅根据上文 BQL 结果重新作答；需要合计请说明将使用哪条查询中的数字，不要心算。'
)

GUARD_DISCLAIMER = (
    '\n\n> **提示**：部分金额可能未完全来自账本查询结果，请以「查询详情」中的 BQL 结果为准。'
)


class _QueryPreview(Protocol):
    result_preview: str


@dataclass(frozen=True)
class NumberValidationResult:
    ok: bool
    reason: str = ''


def _is_year_like(value: Decimal, raw: str) -> bool:
    if '.' in raw:
        return False
    digits = raw.lstrip('-').replace(',', '')
    if len(digits) != 4:
        return False
    year = int(digits)
    return 1900 <= year <= 2100


def extract_amounts(text: str) -> list[Decimal]:
    """从文本中提取疑似金额的数字（忽略四位年份）。"""
    amounts: list[Decimal] = []
    seen: set[Decimal] = set()
    for match in _AMOUNT_PATTERN.finditer(text):
        raw = match.group(1)
        fractional = match.group(2)
        normalized = raw.replace(',', '')
        if fractional is not None:
            normalized = f'{normalized}.{fractional}'
        try:
            value = Decimal(normalized)
        except InvalidOperation:
            continue
        if _is_year_like(value, raw):
            continue
        if value in seen:
            continue
        seen.add(value)
        amounts.append(value)
    return amounts


def _amount_in_source(amount: Decimal, source_text: str, *, tolerance: Decimal) -> bool:
    for candidate in extract_amounts(source_text):
        if abs(candidate - amount) <= tolerance:
            return True
    return False


def _allows_zero_amount(amount: Decimal, source_text: str, *, tolerance: Decimal) -> bool:
    if amount != 0:
        return False
    if _amount_in_source(amount, source_text, tolerance=tolerance):
        return True
    if _NORMALIZED_ZERO.search(source_text):
        return True
    if 'account' not in source_text.lower():
        return False
    for line in source_text.splitlines():
        stripped = line.strip()
        if not stripped or set(stripped) <= {'-', ' '}:
            continue
        if stripped.lower().startswith('account') or 'sum' in stripped.lower():
            continue
        if stripped.startswith('... ('):
            continue
        if not _AMOUNT_SUFFIX.search(stripped):
            return True
    return False


def validate_reply_numbers(
    reply: str,
    queries: list[_QueryPreview],
    *,
    tolerance: Decimal = Decimal('0.01'),
) -> NumberValidationResult:
    """判断回复中的金额是否均能在 BQL 结果中找到。"""
    reply_body = reply.split('---')[0].split('查询详情')[0]
    reply_amounts = extract_amounts(reply_body)
    if not reply_amounts:
        return NumberValidationResult(ok=True)

    if not queries:
        return NumberValidationResult(ok=False, reason='回复含金额但未执行 BQL 查询')

    source_text = '\n'.join(q.result_preview for q in queries)
    for amount in reply_amounts:
        if _amount_in_source(amount, source_text, tolerance=tolerance):
            continue
        if _allows_zero_amount(amount, source_text, tolerance=tolerance):
            continue
        return NumberValidationResult(
            ok=False,
            reason=f'金额 {amount} 未出现在查询结果中',
        )

    if _TOTAL_KEYWORD_PATTERN.search(reply_body):
        for amount in reply_amounts:
            if _amount_in_source(amount, source_text, tolerance=tolerance):
                continue
            if _allows_zero_amount(amount, source_text, tolerance=tolerance):
                continue
            return NumberValidationResult(
                ok=False,
                reason=f'合计相关金额 {amount} 未出现在查询结果中',
            )

    return NumberValidationResult(ok=True)


def apply_guard_disclaimer(reply: str) -> str:
    if GUARD_DISCLAIMER.strip() in reply:
        return reply
    return f'{reply.rstrip()}{GUARD_DISCLAIMER}'
