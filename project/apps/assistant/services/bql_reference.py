"""经 beanquery 0.2.0 验证的 BQL 能力说明，供 LLM 参考。"""

BQL_DOCS_URL = 'https://beancount.github.io/docs/beancount_query_language/'


def build_bql_capability_reference() -> str:
    """返回精简、可执行的 BQL 能力文档。"""
    return f"""
BQL 能力说明（beanquery 实际支持子集，生成查询时请严格遵守）：

【常用列】
- 交易级：date, year, month, payee, narration, tags
- posting 级：account, position, number（纯数值；Expenses 为正，Income 常为负）

【WHERE 允许的比较】
- 账户：account ~ 'Expenses' 或 account ~ '^Expenses'（正则）
- 日期/整数：year = 2026 AND month = 6；date >= 2026-01-01
- 金额过滤（支出）：number > 100
- 金额过滤（收入绝对值）：number < -100
- 标签（精确匹配）：'Discretionary' IN tags 或 'Event/2025-05-01' IN tags
- 标签名须与「平台标签目录」中的完整路径一致（含父级，如 Category/EDUCATION）
- 标签可与 account ~、year/month 等条件 AND 组合

【WHERE 禁止写法】
- 禁止 units(position) > N 或 units(position) < N（不支持，会编译失败）
- 禁止 position > N 或 position < N
- 禁止 tags ~ '...'（beanquery 不支持 set 正则匹配，会编译失败）
- 禁止在 WHERE 中使用 sum/count/avg 等聚合函数
- 禁止使用 HAVING 子句
- 助手场景不要写 FROM 子句，直接用 WHERE 过滤 postings

【SELECT 聚合】
- 汇总：SELECT account, sum(units(position)) ... GROUP BY account
- 单列总额：SELECT sum(units(position)) WHERE account ~ '^Assets:Receivable'
- 聚合函数只能出现在 SELECT，不能出现在 WHERE

【余额与结构分析（应收/资产/负债/收入）】
- 账户累计余额 = 该账户全部 postings 的 sum(units(position))（与 Fava 余额口径一致）
- 各子账户余额：
  SELECT account, sum(units(position)) WHERE account ~ '^Assets:Receivable' GROUP BY account
- 某类账户总额：
  SELECT sum(units(position)) WHERE account ~ '^Assets:Receivable'
- 各负债账户欠款：
  SELECT account, sum(units(position)) WHERE account ~ '^Liabilities' GROUP BY account
- 按交易对方汇总（需先锁定具体 account 正则）：
  SELECT payee, sum(units(position)) WHERE account ~ '^Assets:Receivable:Person' GROUP BY payee
- 禁止拉取大量明细行后在回复中手动求和；多账户合计必须用上述聚合查询
- 零余额：返回账户行但 sum 列为空白 → 余额为 0（与 Fava 一致），不是查询失败；直接告知用户「当前余额为 0」，勿换 OR / $ 锚点反复重试
- 区分两种「空」：(无结果)/无数据行 → 账户或时间可能不对；有账户行 + 空白 sum → 余额为 0

【标签筛选推荐写法】
某标签本月支出总额：
SELECT sum(units(position)) WHERE 'Discretionary' IN tags AND account ~ '^Expenses' AND year = YYYY AND month = M

某标签交易明细：
SELECT date, payee, narration, account, units(position) WHERE 'Event/2025-05-01' IN tags ORDER BY date DESC LIMIT 20

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
