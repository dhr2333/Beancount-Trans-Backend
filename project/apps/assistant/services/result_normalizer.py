"""将 BQL 零余额的空白 sum 列归一化为可读金额。"""
import re

_SUM_AGGREGATE = re.compile(r'\bsum\s*\(\s*(?:units\s*\(\s*position\s*\)|position)\s*\)', re.IGNORECASE)
_AMOUNT_SUFFIX = re.compile(r'\d+(?:\.\d+)?\s*[A-Z]{3}\s*$')
_SEPARATOR_LINE = re.compile(r'^[\s\-]+$')


def _is_sum_balance_query(bql: str) -> bool:
    return bool(_SUM_AGGREGATE.search(bql))


def _is_table_header(line: str) -> bool:
    lowered = line.lower()
    return 'account' in lowered or 'sum' in lowered or lowered.strip() == 's'


def _is_data_row(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if _SEPARATOR_LINE.match(stripped):
        return False
    if stripped.startswith('... ('):
        return False
    if _is_table_header(stripped):
        return False
    return True


def normalize_zero_balance_sums(result_text: str, bql: str, currency: str = 'CNY') -> str:
    """余额聚合查询中，空白 sum 列补为 0.00 {currency}。"""
    if not result_text or result_text.strip() == '(无结果)':
        return result_text
    if not _is_sum_balance_query(bql):
        return result_text

    lines = result_text.splitlines()
    if not any(_is_table_header(line) for line in lines):
        return result_text

    normalized: list[str] = []
    changed = False
    zero_label = f'0.00 {currency}'

    for line in lines:
        if _is_data_row(line) and not _AMOUNT_SUFFIX.search(line.rstrip()):
            normalized.append(f'{line.rstrip()}  {zero_label}')
            changed = True
        else:
            normalized.append(line)

    return '\n'.join(normalized) if changed else result_text
