"""BQL 只读安全校验。"""
import re

_FORBIDDEN_KEYWORDS = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|ATTACH|DETACH|PRAGMA)\b',
    re.IGNORECASE,
)

_UNITS_POSITION_COMPARE = re.compile(
    r'units\s*\(\s*position\s*\)\s*[<>]',
    re.IGNORECASE,
)

_POSITION_COMPARE = re.compile(
    r'\bposition\s*[<>]',
    re.IGNORECASE,
)

_WHERE_AGGREGATE = re.compile(
    r'\b(sum|count|avg|min|max)\s*\(',
    re.IGNORECASE,
)

_WHERE_CLAUSE_END = re.compile(
    r'\b(GROUP BY|ORDER BY|LIMIT)\b',
    re.IGNORECASE,
)

_HAVING_CLAUSE = re.compile(r'\bHAVING\b', re.IGNORECASE)

_TAGS_REGEX = re.compile(r'\btags\s*~', re.IGNORECASE)


class BQLValidationError(ValueError):
    """BQL 校验失败。"""

_WHERE_AGGREGATE_ERROR = (
    'WHERE 中不能使用聚合函数（sum/count 等）。'
    '请移到 SELECT 并使用 GROUP BY；若需按金额排序，'
    '在 GROUP BY 后使用 ORDER BY sum(units(position)) DESC。'
)


def _extract_where_clause(normalized: str) -> str:
    """返回 WHERE 与 GROUP BY/ORDER BY/LIMIT 之间的条件子串（不含 WHERE 关键字）。"""
    where_match = re.search(r'\bWHERE\b', normalized, re.IGNORECASE)
    if not where_match:
        return ''
    rest = normalized[where_match.end():]
    end_match = _WHERE_CLAUSE_END.search(rest)
    if end_match:
        return rest[:end_match.start()]
    return rest


def _check_unsupported_patterns(normalized: str) -> None:
    if _HAVING_CLAUSE.search(normalized):
        raise BQLValidationError('BQL 不支持 HAVING 子句。请简化查询或只用 WHERE + GROUP BY。')

    if _TAGS_REGEX.search(normalized):
        raise BQLValidationError(
            'WHERE 中不支持 tags ~ 正则匹配。'
            '请改用 \'完整标签路径\' IN tags（标签路径见平台标签目录）。'
        )

    if _UNITS_POSITION_COMPARE.search(normalized):
        raise BQLValidationError(
            'WHERE 中不支持 units(position) >/< 比较。'
            '请改用 number > N（支出）或 ORDER BY units(position) DESC LIMIT N。'
        )

    if _POSITION_COMPARE.search(normalized):
        raise BQLValidationError(
            'WHERE 中不支持 position >/< 比较。'
            '请改用 number > N 或 ORDER BY units(position) DESC LIMIT N。'
        )

    where_clause = _extract_where_clause(normalized)
    if where_clause and _WHERE_AGGREGATE.search(where_clause):
        raise BQLValidationError(_WHERE_AGGREGATE_ERROR)


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

    _check_unsupported_patterns(normalized)

    return normalized
