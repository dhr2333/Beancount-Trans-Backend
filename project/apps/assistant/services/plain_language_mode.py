"""简明表达模式：会话只涉及共享账本时，用面向非技术用户的通俗措辞回答。"""
from __future__ import annotations

from typing import Any

PLAIN_LANGUAGE_BLOCK = """【简明表达模式】
当前对话只涉及他人共享的账本，使用者可能不了解记账术语。请在**不减少分析深度**的前提下，把表达降到最低理解门槛：

1. 用日常口语回答，避免专业术语：不要出现 BQL、posting、复式记账、借贷、正则、聚合、GROUP BY、account/position/units、英文账户路径（如 Expenses:Food）等字样。
2. 提到账户或类目时，用平台账户目录里的中文描述（如「餐饮」「交通」）；没有描述时用最通俗的说法，不要写账户路径。
3. 结论先行：第一句话直接回答用户的问题（金额、对比结论，或「没有查到」），再补充必要的 1–2 句说明。
4. 措辞明确：金额写清币种与单位（如「1,200.00 元」）；涉及时间写清「几月/哪天」；涉及多个账本时明确「这是〈谁〉账本里的」。
5. 保持简洁：不堆砌用户没问到的细节；表格列数尽量少（≤ 3 列），只保留用户关心的信息；不输出查询语法与推导过程。
6. 分析照做（趋势、对比、查找异常等仍按需完成），但只讲通俗结论，不展示技术推导。
"""


def detect_plain_language_mode(
    prior_queries: list[dict[str, Any]] | None,
    *,
    self_ledger_available: bool,
) -> bool:
    """会话级判定是否启用简明表达。

    以「会话内已完成查询的账本来源」为准：
    - 出现过本人账本（ledger 为 'self' 或缺失/空，兼容旧数据）→ 常规模式；
    - 只出现过共享账本查询 → 简明模式；
    - 尚无任何有效查询记录 → 无本人账本时简明，否则常规（保持现状）。
    """
    ledgers = {
        (q.get('ledger') or 'self')
        for q in (prior_queries or [])
        if q.get('bql')
    }
    if 'self' in ledgers:
        return False
    if ledgers:
        return True
    return not self_ledger_available
