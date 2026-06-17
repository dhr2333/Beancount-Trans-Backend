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

【WHERE 禁止写法】
- 禁止 units(position) > N 或 units(position) < N（不支持，会编译失败）
- 禁止 position > N 或 position < N
- 禁止在 WHERE 中使用 sum/count/avg 等聚合函数
- 禁止使用 HAVING 子句
- 助手场景不要写 FROM 子句，直接用 WHERE 过滤 postings

【SELECT 聚合】
- 汇总：SELECT account, sum(units(position)) ... GROUP BY account
- 聚合函数只能出现在 SELECT，不能出现在 WHERE

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

完整参考（仅供人工查阅）：{BQL_DOCS_URL}
""".strip()
