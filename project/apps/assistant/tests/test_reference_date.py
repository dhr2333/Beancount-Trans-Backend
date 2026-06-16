from datetime import date

import pytest

from project.apps.assistant.services.reference_date import build_reference_date_context


class TestReferenceDate:
    def test_build_context_for_june(self):
        ctx = build_reference_date_context(date(2026, 6, 16))
        assert '基准日期（今天）: 2026-06-16' in ctx
        assert '当前年月: 2026 年 6 月' in ctx
        assert '上月: 2026 年 5 月' in ctx
        assert 'year = 2026 AND month = 6' in ctx
        assert 'year = 2026 AND month = 5' in ctx

    def test_build_context_january_last_month(self):
        ctx = build_reference_date_context(date(2026, 1, 10))
        assert '上月: 2025 年 12 月' in ctx
        assert 'year = 2025 AND month = 12' in ctx
