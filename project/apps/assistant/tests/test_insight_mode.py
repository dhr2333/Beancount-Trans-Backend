from project.apps.assistant.services.insight_mode import (
    detect_insight_mode,
    get_last_user_message,
)


class TestGetLastUserMessage:
    def test_returns_last_user_message(self):
        messages = [
            {'role': 'user', 'content': '第一个问题'},
            {'role': 'assistant', 'content': '回答'},
            {'role': 'user', 'content': '第二个问题'},
        ]
        assert get_last_user_message(messages) == '第二个问题'

    def test_returns_empty_when_no_user(self):
        assert get_last_user_message([{'role': 'assistant', 'content': 'hi'}]) == ''


class TestDetectInsightMode:
    def test_insight_keywords_trigger(self):
        assert detect_insight_mode('提供一份消费洞察') is True
        assert detect_insight_mode('有什么令人意外的消费发现？') is True
        assert detect_insight_mode('帮我写一份月度总结') is True
        assert detect_insight_mode('分析一下我的支出结构') is True
        assert detect_insight_mode('给我一份消费报告') is True

    def test_broad_short_questions_trigger(self):
        assert detect_insight_mode('帮我看看账本') is True
        assert detect_insight_mode('账本怎么样') is True

    def test_factual_questions_do_not_trigger(self):
        assert detect_insight_mode('本月总支出是多少？') is False
        assert detect_insight_mode('各资产账户余额是多少？') is False
        assert detect_insight_mode('上个月餐饮花了多少？') is False
        assert detect_insight_mode('餐饮多少？') is False

    def test_large_expense_list_is_factual(self):
        assert detect_insight_mode('最近有哪些大额消费？') is False

    def test_empty_message(self):
        assert detect_insight_mode('') is False
        assert detect_insight_mode('   ') is False

    def test_analysis_with_factual_still_triggers(self):
        assert detect_insight_mode('分析个人应收款') is True
