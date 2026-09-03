"""从 beanquery 结果抽取来源区证据切片（摘要 + Top 行）。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Sequence

EVIDENCE_MAX_ROWS = 5

# 列名映射为简短中文（未知列保留原名）
COLUMN_LABELS = {
    'date': '日期',
    'payee': '收款人',
    'narration': '叙述',
    'account': '账户',
    'units(position)': '金额',
    'sum(units(position))': '合计',
    'sum(position)': '合计',
    'position': '金额',
    'number': '数值',
    'year': '年',
    'month': '月',
    'tags': '标签',
    'links': '链接',
}


@dataclass
class QueryEvidence:
    summary: str
    columns: list[str]
    rows: list[list[str]]
    row_count: int
    truncated: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            'summary': self.summary,
            'columns': self.columns,
            'rows': self.rows,
            'row_count': self.row_count,
            'truncated': self.truncated,
        }


def _column_name(col: Any) -> str:
    name = getattr(col, 'name', None) or str(col)
    return str(name)


def _column_label(name: str) -> str:
    return COLUMN_LABELS.get(name, name)


def format_cell(value: Any, *, path_map: dict[str, str] | None = None) -> str:
    if value is None:
        return ''
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f'{value:f}'.rstrip('0').rstrip('.') if '.' in f'{value:f}' else str(value)
    text = str(value).strip()
    if path_map and text in path_map:
        return f'{path_map[text]}（{text}）'
    # Inventory 常带括号：(50.00 CNY)
    if text.startswith('(') and text.endswith(')') and ' ' in text:
        inner = text[1:-1].strip()
        if inner:
            return inner
    return text


def _preferred_columns(names: list[str]) -> list[str]:
    """明细优先展示这些列；其余按原顺序补齐，最多 5 列。"""
    preferred = ['date', 'payee', 'narration', 'account', 'units(position)', 'sum(units(position))', 'sum(position)', 'position']
    ordered: list[str] = []
    for name in preferred:
        if name in names and name not in ordered:
            ordered.append(name)
    for name in names:
        if name not in ordered:
            ordered.append(name)
    return ordered[:5]


def build_query_evidence(
    description: Sequence[Any],
    rows: Sequence[Sequence[Any]],
    *,
    row_count: int,
    truncated: bool,
    path_map: dict[str, str] | None = None,
    max_rows: int = EVIDENCE_MAX_ROWS,
) -> QueryEvidence:
    names = [_column_name(col) for col in description]
    selected = _preferred_columns(names)
    indices = [names.index(name) for name in selected]
    labels = [_column_label(name) for name in selected]

    evidence_rows: list[list[str]] = []
    for row in rows[:max_rows]:
        cells: list[str] = []
        for idx, name in zip(indices, selected):
            value = row[idx] if idx < len(row) else None
            cell_map = path_map if name == 'account' else None
            cells.append(format_cell(value, path_map=cell_map))
        evidence_rows.append(cells)

    shown = len(evidence_rows)
    if row_count == 0:
        summary = '无匹配结果'
    elif truncated or shown < row_count:
        summary = f'共 {row_count} 行，显示前 {shown} 行'
    else:
        summary = f'共 {row_count} 行'

    return QueryEvidence(
        summary=summary,
        columns=labels,
        rows=evidence_rows,
        row_count=row_count,
        truncated=truncated or shown < row_count,
    )


def evidence_from_dict(data: dict[str, Any] | None) -> QueryEvidence | None:
    if not data or not isinstance(data, dict):
        return None
    columns = data.get('columns') or []
    rows = data.get('rows') or []
    if not isinstance(columns, list) or not isinstance(rows, list):
        return None
    return QueryEvidence(
        summary=str(data.get('summary') or ''),
        columns=[str(c) for c in columns],
        rows=[[str(cell) for cell in row] for row in rows if isinstance(row, list)],
        row_count=int(data.get('row_count') or len(rows)),
        truncated=bool(data.get('truncated')),
    )
