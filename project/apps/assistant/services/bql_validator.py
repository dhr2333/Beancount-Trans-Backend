"""BQL 只读安全校验。"""
import re

_FORBIDDEN_KEYWORDS = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|ATTACH|DETACH|PRAGMA)\b',
    re.IGNORECASE,
)


class BQLValidationError(ValueError):
    """BQL 校验失败。"""


def validate_bql(query: str) -> str:
    """校验 BQL 为只读 SELECT 查询，返回规范化后的查询字符串。"""
    if not query or not query.strip():
        raise BQLValidationError('查询不能为空')

    normalized = query.strip().rstrip(';').strip()
    if not normalized:
        raise BQLValidationError('查询不能为空')

    if ';' in normalized:
        raise BQLValidationError('不允许多条语句')

    if not re.match(r'^SELECT\b', normalized, re.IGNORECASE):
        raise BQLValidationError('仅允许 SELECT 查询')

    if _FORBIDDEN_KEYWORDS.search(normalized):
        raise BQLValidationError('查询包含不允许的关键字')

    return normalized
