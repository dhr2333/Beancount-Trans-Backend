"""洞察模式：自动识别开放性分析问题并注入专用 prompt 策略。"""

INSIGHT_KEYWORDS = (
    '洞察',
    '总结',
    '发现',
    '分析',
    '报告',
    '趋势',
    '意外',
    '惊喜',
    '对比',
    '规律',
    '亮点',
    '消费洞察',
    '月度总结',
    '财务总结',
    '消费报告',
    '账本怎么样',
    '帮我看看',
    '有什么',
    '看看账本',
    '消费习惯',
    '支出结构',
    '收支情况',
)

BROAD_QUESTION_PHRASES = (
    '帮我看看',
    '账本怎么样',
    '有什么',
    '看看账本',
    '账本如何',
    '账本情况',
)

FACTUAL_PATTERNS = (
    '多少',
    '余额',
    '花了多少',
    '收入多少',
    '支出多少',
    '总共',
    '合计',
    '是多少',
    '有哪些',
    '列出',
    '查询',
)

INSIGHT_MODE_BLOCK = """
【洞察模式】
用户提出了开放性分析类问题。你的目标是发现**令人兴奋、可分享**的数据规律，而非罗列全科目清单。

查询策略（在 max_bql_runs 限制内，按优先级执行）：
1. **跨期对比（必做）**：至少 1 条近 3–6 月趋势（GROUP BY year, month）或类目/标签跨月对比。
2. **多维线索**（按场景组合，不只盯 account）：
   - payee / narration：TOP 商家、备注关键词（物业费、机票、退款等）
   - tags：对照「平台标签目录」，跨月标签支出、某月首次出现某标签
   - links：对大额/异常交易用 'link-id' IN links，追同一 link 下关联 posting（退款、拆分、转账）
   - meta + 日期：FROM entries 拉含 time/uuid/status 的明细，分析消费时段或重复 uuid
   - Balance / Pad：FROM entries 查 type='balance' / type='pad'，解释对账偏差、补账是否导致某月突增
3. **主动追溯（必做）**：从当期发现 1–2 个「有故事」的线索（突变金额、新 payee、罕见 tag、link 关联退款等），
   即使用户未要求「意外发现」，也必须再查 1 条历史/关联查询（同 payee 跨月、同 link 全量、同 tag 跨月等）。

BQL 预算优先级：跨期趋势 → 环比/类目对比 → 线索追溯（payee/link/tag）→ entries 明细（meta/Balance/Pad）。

回答结构：
- **开头**：2–3 条具体亮点（数字 + 跨期/跨维度对比），例如「4 月物业费 3,669 元，为其他月 6–12 倍，narration 指向一次性缴纳」。
- **中间**：精简表格，只支撑上述亮点；禁止把占比排序当「洞察」复读。
- **禁止**：无 BQL 依据的推测（推测须标注并引用 payee/narration/tag/link/meta）。
- **展示**：仍遵守「描述（账户路径）」格式。
"""


def get_last_user_message(messages: list[dict]) -> str:
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            return (msg.get('content') or '').strip()
    return ''


def detect_insight_mode(user_message: str) -> bool:
    text = (user_message or '').strip()
    if not text:
        return False

    has_insight_keyword = any(kw in text for kw in INSIGHT_KEYWORDS)

    is_broad_short = len(text) <= 20 and any(phrase in text for phrase in BROAD_QUESTION_PHRASES)

    if has_insight_keyword or is_broad_short:
        is_pure_factual = (
            any(p in text for p in FACTUAL_PATTERNS)
            and not has_insight_keyword
            and not is_broad_short
        )
        if is_pure_factual:
            return False
        return True

    return False
