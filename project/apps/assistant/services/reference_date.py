"""为 AI 助手提供以当前日期为基准的时间上下文。"""
from datetime import date

from django.utils import timezone


def get_reference_date() -> date:
    """返回助手使用的基准日期（服务器本地时区下的今天）。"""
    return timezone.localdate()


def build_reference_date_context(reference_date: date | None = None) -> str:
    """生成基准日期说明，供 LLM 解析「本月」「上月」等相对时间。"""
    today = reference_date or get_reference_date()

    if today.month == 1:
        last_month_year, last_month = today.year - 1, 12
    else:
        last_month_year, last_month = today.year, today.month - 1

    return '\n'.join([
        f'基准日期（今天）: {today.isoformat()}',
        f'当前年月: {today.year} 年 {today.month} 月',
        f'上月: {last_month_year} 年 {last_month} 月',
        '相对时间解读：',
        f'  - 「今天/今日」→ date = {today.isoformat()}',
        f'  - 「本月」→ year = {today.year} AND month = {today.month}',
        f'  - 「上月/上个月」→ year = {last_month_year} AND month = {last_month}',
        f'  - 「今年」→ year = {today.year}',
        f'  - 「最近 N 天」→ date >= {today.isoformat()} 往前推算（用 date 范围过滤）',
    ])
