from datetime import date

import pytest

from project.apps.assistant.services.assistant_service import build_system_prompt
from project.apps.assistant.services.bql_reference import build_bql_capability_reference
from project.apps.assistant.services.schema_provider import (
    build_bql_examples,
    build_insight_bql_examples,
    build_user_specific_bql_examples,
    get_ledger_context,
)


class TestBuildBqlExamples:
    def test_includes_current_and_last_month(self):
        text = build_bql_examples(date(2026, 6, 16))
        assert 'year = 2026 AND month = 6' in text
        assert 'year = 2026 AND month = 5' in text
        assert '【问题】本月总支出是多少？' in text
        assert '【BQL】' in text
        assert "account ~ '^Expenses'" in text

    def test_includes_generic_assets_and_liabilities_examples(self):
        text = build_bql_examples(date(2026, 6, 16))
        assert "^Assets'" in text or "account ~ '^Assets'" in text
        assert '^Liabilities' in text
        assert '各负债账户欠款' in text
        assert '非 Fava 余额' not in text

    def test_uses_tag_placeholders_not_fixed_tags(self):
        text = build_bql_examples(date(2026, 6, 16))
        assert "'完整标签路径' IN tags" in text
        assert "'Discretionary' IN tags" not in text
        assert "'Event/2025-05-01' IN tags" not in text
        assert '某标签本月支出花了多少' in text

    def test_does_not_include_user_specific_sub_accounts(self):
        text = build_bql_examples(date(2026, 6, 16))
        assert '^Assets:Receivable' not in text
        assert '^Assets:Savings:Cash' not in text
        assert '^Assets:Savings:Web:AliPay' not in text
        assert '现金还有多少' not in text
        assert '支付宝余额是多少' not in text

    def test_january_last_month_is_previous_december(self):
        text = build_bql_examples(date(2026, 1, 15))
        assert 'year = 2026 AND month = 1' in text
        assert 'year = 2025 AND month = 12' in text

    def test_includes_generic_sub_account_placeholder(self):
        text = build_bql_examples(date(2026, 6, 16))
        assert "account ~ '^Assets:...'" in text
        assert 'sum 列为空白，表示余额为 0' in text
        assert '父账户行仅含直接 posting' in text

    def test_includes_parent_child_food_examples(self):
        text = build_bql_examples(date(2026, 6, 16))
        assert '本月餐饮（含子科目）总支出' in text
        assert '本月餐饮各子科目分别花了多少' in text
        assert "^Expenses:Food'" in text

    def test_large_expense_uses_number_not_units_compare(self):
        text = build_bql_examples(date(2026, 6, 16))
        assert 'number > 100' in text
        assert 'units(position) >' not in text
        assert 'ORDER BY units(position) DESC' in text

    def test_includes_group_by_order_by_sum_example(self):
        text = build_bql_examples(date(2026, 6, 16))
        assert '本月支出科目按金额从高到低排序' in text
        assert 'ORDER BY sum(units(position)) DESC' in text

    def test_includes_income_examples(self):
        text = build_bql_examples(date(2026, 6, 16))
        assert '本月总收入是多少' in text
        assert '本月各收入科目分别是多少' in text
        assert '本月工资收入多少' in text
        assert "account ~ '^Income'" in text
        assert 'Income 的 sum 为负表示收入金额' in text


class TestBuildInsightBqlExamples:
    def test_includes_cross_period_and_entries_patterns(self):
        text = build_insight_bql_examples(date(2026, 6, 16))
        assert '洞察模式 BQL 示例' in text
        assert 'GROUP BY year, month' in text
        assert 'FROM entries' in text
        assert 'IN links' in text
        assert "'完整标签路径' IN tags" in text
        assert "type IN ('balance', 'pad')" in text
        assert 'year = 2026 AND month = 6' in text


class TestBuildUserSpecificBqlExamples:
    @pytest.mark.django_db
    def test_generates_examples_from_user_catalog(self, user, bean_file, platform_metadata):
        text = build_user_specific_bql_examples(
            user,
            reference_date=date(2026, 6, 16),
            ledger_accounts=['Assets:Cash', 'Expenses:Food', 'Income:Salary'],
        )
        assert '账本相关 BQL 示例' in text
        assert "^Assets:Cash'" in text
        assert '现金余额是多少' in text
        assert "^Expenses:Food'" in text
        assert '本月餐饮花了多少' in text
        assert "'Discretionary' IN tags" in text

    @pytest.mark.django_db
    def test_returns_empty_without_catalog_matches(self, user):
        text = build_user_specific_bql_examples(user, ledger_accounts=[])
        assert text == ''


class TestBqlCapabilityReference:
    def test_documents_number_and_forbids_units_compare(self):
        ref = build_bql_capability_reference()
        assert 'number > 100' in ref
        assert '禁止 units(position) > N' in ref
        assert 'beancount.github.io' in ref

    def test_documents_balance_analysis_patterns(self):
        ref = build_bql_capability_reference()
        assert '余额与结构分析' in ref
        assert "account ~ '^Assets'" in ref
        assert '^Assets:Receivable' not in ref
        assert '禁止拉取大量明细行' in ref
        assert '平台账户目录' in ref

    def test_documents_tag_filter_syntax(self):
        ref = build_bql_capability_reference()
        assert "'完整标签路径' IN tags" in ref
        assert "'Discretionary' IN tags" not in ref
        assert '禁止 tags ~' in ref
        assert '标签筛选推荐写法' in ref

    def test_documents_zero_balance_semantics(self):
        ref = build_bql_capability_reference()
        assert '零余额' in ref
        assert '空白 sum' in ref
        assert '禁止为此重试' in ref

    def test_documents_order_by_sum_after_group_by(self):
        ref = build_bql_capability_reference()
        assert 'ORDER BY sum(units(position)) DESC' in ref
        assert '无数据行' in ref

    def test_documents_account_hierarchy_semantics(self):
        ref = build_bql_capability_reference()
        assert '账户层级与汇总口径' in ref
        assert '父账户' in ref
        assert '子树总额' in ref
        assert '无 posting' in ref

    def test_documents_double_entry_sign_convention(self):
        ref = build_bql_capability_reference()
        assert '复式记账符号约定' in ref
        assert 'Income：累计为负' in ref
        assert '禁止将 Income 负余额说成「亏损」' in ref

    def test_insight_mode_includes_entries_and_links(self):
        ref = build_bql_capability_reference(insight_mode=True)
        assert '洞察分析推荐写法' in ref
        assert 'FROM entries' in ref
        assert 'IN links' in ref
        assert 'Balance / Pad' in ref
        assert 'postings.meta 不含 time' in ref


class TestBuildSystemPrompt:
    def test_includes_reference_date_and_examples(self):
        prompt = build_system_prompt(date(2026, 6, 16))
        assert '基准日期（今天）: 2026-06-16' in prompt
        assert 'BQL 查询示例' in prompt
        assert '【BQL】' in prompt
        assert 'BQL 能力说明' in prompt
        assert 'number > 100' in prompt
        assert '^Assets:Savings:Cash' not in prompt
        assert '账户层级' in prompt
        assert '父账户行仅含直接 posting' in prompt
        assert '复式记账符号' in prompt
        assert 'Income 累计为负表示收入' in prompt
        assert '【洞察模式】' not in prompt

    def test_insight_mode_includes_insight_block_and_examples(self):
        prompt = build_system_prompt(date(2026, 6, 16), insight_mode=True)
        assert '【洞察模式】' in prompt
        assert '主动追溯' in prompt
        assert '洞察模式 BQL 示例' in prompt
        assert 'FROM entries' in prompt
        assert 'IN links' in prompt
        assert 'GROUP BY year, month' in prompt
        assert '洞察分析推荐写法' in prompt
        assert 'Balance / Pad' in prompt


@pytest.mark.django_db
class TestGetLedgerContext:
    def test_includes_bql_examples_and_accounts(self, user, bean_file):
        context = get_ledger_context(user, reference_date=date(2026, 6, 16))
        assert 'BQL 查询示例' in context
        assert '【BQL】' in context
        assert 'year = 2026 AND month = 6' in context
        assert 'Expenses:Food' in context
        assert 'BQL 能力说明' in context
        assert '禁止 units(position) > N' in context
        assert '^Assets:Savings:Cash' not in context

    def test_includes_platform_catalog(self, user, bean_file, platform_metadata):
        context = get_ledger_context(user, reference_date=date(2026, 6, 16))
        assert '平台账户目录' in context
        assert 'Expenses:Food → 餐饮' in context
        assert '平台标签目录' in context
        assert 'Discretionary → 非必要支出' in context
        assert '账本实际出现的账户' in context

    def test_includes_user_specific_examples(self, user, bean_file, platform_metadata):
        context = get_ledger_context(user, reference_date=date(2026, 6, 16))
        assert '账本相关 BQL 示例' in context
        assert "^Assets:Cash'" in context
        assert '本月餐饮花了多少' in context
