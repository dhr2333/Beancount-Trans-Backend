"""简明表达模式：回答来自共享账本数据时，用面向非技术用户的通俗措辞作答。"""
from __future__ import annotations

# 提问中若出现这些字眼，可能同时涉及本人账本口径，交回模型按条件规则判断（保守处理）。
SELF_LEDGER_TOKENS = ('我', '本人', '自己')

PLAIN_LANGUAGE_BLOCK = """【简明表达模式】
当本次回答的数据来自共享账本（没有使用本人账本的数据）时，必须遵守以下规则；
本块规则优先级高于上文所有格式规则，如有冲突以本块为准：

1. 不要出现任何技术字眼：BQL、查询、SQL、posting、复式记账、借贷、正则、聚合、GROUP BY、account/position/units、英文账户路径（如 Expenses:Food）等；也不要说明数据是「查询/数据库/BQL 得到的」——共享账本的使用者无法进行这类查询。
2. 提到类目/账户时一律用平台账户目录里的中文描述；**不要写账户路径，也不要有父子层级**：把类目**平铺成一层**直接列出（例如直接列「外卖 500 元」，不要写「餐饮 → 外卖」，也不要缩进子项或同时给出父类目小计与子类目明细）。
3. 不要说明数据来自哪个账本、来自谁，不写「这是 xxx 账本里的」「来自共享账本」，也不要输出任何来源链接。
4. 不要输出「数据可能不准确」「仅供参考」「受权限限制」「无法保证完整」等免责或不确定措辞；只依据已有结果给出确定结论，查无数据就直接说「没有查到」。
5. 结论先行：第一句话直接回答用户的问题（金额、对比结论，或「没有查到」），再补充必要的 1–2 句说明。
6. 措辞明确：金额写清币种与单位（如「1,200.00 元」）；涉及时间写清「几月/哪天」。
7. 保持简洁：表格列数尽量少（≤ 3 列），只保留用户关心的信息；不输出查询语法与推导过程。
8. 分析照做（趋势、对比、查找异常等仍按需完成），但只讲通俗结论，不展示技术推导。
"""

SHARED_PLAIN_CONDITION_HEADER = """【共享账本数据回答规则】
当前会话可访问共享账本。若本次回答的数据来自共享账本（没有使用本人账本的数据），则按下方「简明表达模式」作答；
若本次回答用到了本人账本的数据，则忽略下方「简明表达模式」，按常规格式作答。
"""


def detect_plain_language_mode(
    *,
    self_ledger_available: bool,
    last_user_message: str = '',
    shared_ledger_keys=(),
) -> bool:
    """是否强制启用简明表达（无需等待查询结果即可判定）。

    与「条件规则」配合使用：
    - 本人账本不存在 → 只可能用共享账本，强制简明；
    - 本次提问点名了共享账本、且没有本人账本口径的字眼 → 强制简明；
    - 其余情况不强制，交由模型按实际数据来源套用条件规则。
    """
    if not self_ledger_available:
        return True

    text = (last_user_message or '').strip()
    if not text:
        return False

    lowered = text.lower()
    mentioned = any(
        str(key).strip() and str(key).strip().lower() in lowered
        for key in (shared_ledger_keys or [])
    )
    if not mentioned:
        return False

    return not any(token in text for token in SELF_LEDGER_TOKENS)


def build_plain_language_prompt_block(*, forced: bool) -> str:
    """构建简明表达提示块：forced 为强制，否则为按数据来源判断的条件规则。"""
    if forced:
        return PLAIN_LANGUAGE_BLOCK
    return f'{SHARED_PLAIN_CONDITION_HEADER}\n{PLAIN_LANGUAGE_BLOCK}'
