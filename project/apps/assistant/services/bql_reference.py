"""经 beanquery 0.2.0 验证的 BQL 能力说明，供 LLM 参考。"""

BQL_DOCS_URL = 'https://beancount.github.io/docs/beancount_query_language/'


def build_bql_capability_reference(*, insight_mode: bool = False) -> str:
    """返回精简、可执行的 BQL 能力文档。"""
    from_clause_note = (
        '洞察模式下允许 FROM entries 查 meta/Balance/Pad（见下方「洞察分析」）；'
        '常规金额查询默认 postings 表，不写 FROM'
        if insight_mode
        else '助手场景不要写 FROM 子句，直接用 WHERE 过滤 postings'
    )
    base = f"""
BQL 能力说明（beanquery 实际支持子集，生成查询时请严格遵守）：

【常用列】
- 交易级：date, year, month, payee, narration, tags, links
- posting 级：account, position, number（纯数值；符号含义见下方「复式记账符号约定」）
- entries 表（FROM entries）：type, meta, accounts；用于交易 meta、Balance、Pad

【复式记账符号约定】
- Beancount 为复式记账；sum(units(position)) 的符号有业务含义，与 Fava 一致
- Expenses：累计为正 → 支出金额
- Income：累计为负 → 收入金额（盈利）；累计为正 → 冲销/退款，不是新增收入
- Liabilities：累计为负 → 欠款（负债余额）
- Assets：累计为正 → 资产余额
- 向用户展示 Income/Liabilities 时：用绝对值表述金额，可简短注明「账本中为负属正常」；禁止将 Income 负余额说成「亏损」
- BQL 写法不变：收入汇总用 account ~ '^Income' + sum(units(position))；筛大额收入用 number < -N

【WHERE 允许的比较】
- 账户：account ~ 'Expenses' 或 account ~ '^Expenses'（正则）
- 商家/备注：payee ~ '关键词'、narration ~ '关键词'（正则语法同 account ~）
- 日期/整数：year = 2026 AND month = 6；date >= 2026-01-01
- 金额过滤（支出）：number > 100
- 金额过滤（收入绝对值）：number < -100
- 标签（精确匹配）：'完整标签路径' IN tags（路径须与「平台标签目录」一致，含父级）
- 关联 link：'link-id' IN links（用于追同一笔 split/退款/转账的多行 posting）
- 标签可与 account ~、year/month 等条件 AND 组合

【WHERE 禁止写法】
- 禁止 units(position) > N 或 units(position) < N（不支持，会编译失败）
- 禁止 position > N 或 position < N
- 禁止 tags ~ '...'（beanquery 不支持 set 正则匹配，会编译失败）
- 禁止 links ~ '...'（同上，links 筛选用 IN）
- 禁止在 WHERE 中使用 sum/count/avg 等聚合函数
- 禁止使用 HAVING 子句
- 禁止 meta ~ '...'（meta 为 dict，WHERE 不支持正则过滤，仅 SELECT 后解读）
- {from_clause_note}

【SELECT 聚合】
- 汇总：SELECT account, sum(units(position)) ... GROUP BY account
- 单列总额：SELECT sum(units(position)) WHERE account ~ '^Assets'
- 聚合函数只能出现在 SELECT，不能出现在 WHERE

【余额与结构分析（应收/资产/负债/收入）】
- 账户累计余额 = 该账户全部 postings 的 sum(units(position))（与 Fava 余额口径一致）
- 子账户路径须先对照「平台账户目录」再写 account ~ 正则，勿臆造路径
- 各子账户余额：
  SELECT account, sum(units(position)) WHERE account ~ '^Assets' GROUP BY account
- 某类账户总额：
  SELECT sum(units(position)) WHERE account ~ '^Assets:...'（... 替换为目录中的子路径）
- 各负债账户欠款：
  SELECT account, sum(units(position)) WHERE account ~ '^Liabilities' GROUP BY account
- 按交易对方汇总（需先锁定具体 account 正则）：
  SELECT payee, sum(units(position)) WHERE account ~ '^Assets:...' GROUP BY payee
- 禁止拉取大量明细行后在回复中手动求和；多账户合计必须用上述聚合查询
- 零余额：返回账户行但 sum 列为空白 → 余额为 0（与 Fava 一致），不是查询失败；直接告知用户「当前余额为 0」，勿换 OR / $ 锚点反复重试
- 区分两种「空」：(无结果)/无数据行 → 账户或时间可能不对；有账户行 + 空白 sum → 余额为 0

【账户层级与汇总口径】
- GROUP BY account 每行 sum = 该账户**直接** posting；父账户行 ≠ 子树总额
- 父账户若本身有 posting，会单独占一行（如 Expenses:Food）；子账户各自独立一行
- 无 posting 的父/子账户不会出现在结果中（与「有 posting 净额 0、sum 列为空白」不同）
- 问某类目总额（如「餐饮花了多少」）：
  SELECT sum(units(position)) WHERE account ~ '^Expenses:Food'（前缀正则，含父账户 + 全部子孙 posting）
- 问各子科目明细：
  SELECT account, sum(units(position)) WHERE account ~ '^Expenses:Food' ... GROUP BY account
  解读时各行独立；勿把父账户行当作该类目总额
- 需要总额时优先用上述 sum 查询，禁止对 GROUP BY 多行手动求和
- account = 'Expenses:Food' 仅父账户直接 posting；account ~ '^Expenses:Food' 含全部子孙

【标签筛选推荐写法】
某标签本月支出总额：
SELECT sum(units(position)) WHERE '完整标签路径' IN tags AND account ~ '^Expenses' AND year = YYYY AND month = M

某标签交易明细：
SELECT date, payee, narration, account, units(position) WHERE '完整标签路径' IN tags ORDER BY date DESC LIMIT 20

【大额消费推荐写法】
方式 A（按金额过滤支出）：
SELECT date, payee, narration, account, units(position)
WHERE account ~ '^Expenses' AND year = YYYY AND month = M AND number > 100
ORDER BY date DESC LIMIT 20

方式 B（按金额排序，更稳）：
SELECT date, payee, narration, account, units(position)
WHERE account ~ '^Expenses' AND year = YYYY AND month = M
ORDER BY units(position) DESC LIMIT 20

【失败处理】
- 查询失败或 (无结果) 时最多再试 1 次，换更宽账户前缀或检查年月
- sum 列为空白但已有账户行：视为余额 0，禁止为此重试

完整参考（仅供人工查阅）：{BQL_DOCS_URL}
""".strip()
    if insight_mode:
        base = f'{base}\n\n{build_insight_bql_capability_supplement()}'
    return base


def build_insight_bql_capability_supplement() -> str:
    """洞察模式追加的 BQL 写法说明。"""
    return """
【洞察分析推荐写法】
跨期趋势（近 3–6 月）：
SELECT year, month, sum(units(position))
WHERE account ~ '^Expenses' AND year = YYYY
GROUP BY year, month

类目跨月对比：
SELECT year, month, sum(units(position))
WHERE account ~ '^Expenses:Home:Utilities' AND year = YYYY
GROUP BY year, month

payee 历史追溯（名称不一致时用较短关键词）：
SELECT year, month, sum(units(position))
WHERE payee ~ '山姆' AND account ~ '^Expenses'
GROUP BY year, month

同 link 关联交易：
SELECT date, payee, narration, account, units(position), links
WHERE 'order-001' IN links AND account ~ '^Expenses'
ORDER BY date

标签跨月：
SELECT year, month, sum(units(position))
WHERE '完整标签路径' IN tags AND account ~ '^Expenses'
GROUP BY year, month

交易 meta（time/uuid/status 等在 transaction meta，postings.meta 不含 time）：
SELECT date, payee, narration, meta, tags, links
FROM entries
WHERE type = 'transaction' AND year = YYYY AND month = M
ORDER BY date DESC LIMIT 20

Balance / Pad 记录（解释对账偏差与补账；不直接产生 Expenses posting）：
SELECT date, type, accounts
FROM entries
WHERE type IN ('balance', 'pad')
ORDER BY date DESC LIMIT 20

【洞察 BQL 边界】
- balances 表不可用，Balance 断言统一走 FROM entries WHERE type='balance'
- meta 不能在 WHERE 正则过滤，拉明细后从结果 dict 解读 time/uuid/status
- links/tags 列为 set，筛选用 '值' IN links / '路径' IN tags
""".strip()
