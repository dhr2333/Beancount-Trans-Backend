import pytest

from project.apps.assistant.models import ChatMessage, ChatSession
from project.apps.assistant.services.assistant_service import query_records_from_dicts
from project.apps.assistant.services.reply_number_guard import validate_reply_numbers
from project.apps.assistant.services.session_service import (
    QUERY_HISTORY_HEADER,
    build_llm_messages,
    collect_prior_query_records,
    format_query_history,
)


@pytest.mark.django_db
class TestFormatQueryHistory:
    def test_empty_queries_returns_empty_string(self):
        assert format_query_history([]) == ''

    def test_formats_bql_and_preview(self):
        text = format_query_history([
            {
                'bql': "SELECT account WHERE account ~ '^Expenses:Food'",
                'result_preview': 'account | sum\nExpenses:Food | 100.00 CNY',
            },
        ])
        assert QUERY_HISTORY_HEADER in text
        assert "SELECT account WHERE account ~ '^Expenses:Food'" in text
        assert '100.00 CNY' in text

    def test_truncates_long_preview(self):
        preview = 'x' * 2000
        text = format_query_history([
            {'bql': 'SELECT 1', 'result_preview': preview},
        ])
        assert '…' in text
        assert len(text) < len(preview) + 100


@pytest.mark.django_db
class TestBuildLlmMessages:
    def test_appends_query_history_to_assistant_content_only_for_llm(self, user):
        session = ChatSession.objects.create(user=user, title='测试')
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_USER,
            content='餐饮多少',
            position=0,
        )
        assistant = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_ASSISTANT,
            content='餐饮支出 100 元。',
            position=1,
            queries=[{
                'bql': "SELECT sum(units(position)) WHERE account ~ '^Expenses:Food'",
                'result_preview': 'sum\n100.00 CNY',
            }],
        )

        messages = build_llm_messages(session)
        assert len(messages) == 2
        assert messages[1]['role'] == 'assistant'
        assert QUERY_HISTORY_HEADER in messages[1]['content']
        assert '餐饮支出 100 元。' in messages[1]['content']

        assistant.refresh_from_db()
        assert QUERY_HISTORY_HEADER not in assistant.content

    def test_skips_incomplete_assistant_messages(self, user):
        session = ChatSession.objects.create(user=user, title='生成中')
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_USER,
            content='问题',
            position=0,
        )
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_ASSISTANT,
            content='',
            position=1,
            generation_status=ChatMessage.STATUS_GENERATING,
        )

        messages = build_llm_messages(session)
        assert messages == [{'role': 'user', 'content': '问题'}]


@pytest.mark.django_db
class TestCollectPriorQueryRecords:
    def test_collects_from_completed_assistant_messages(self, user):
        session = ChatSession.objects.create(user=user, title='续聊')
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_USER,
            content='第一次',
            position=0,
        )
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_ASSISTANT,
            content='第一次回答',
            position=1,
            queries=[{
                'bql': 'SELECT 1',
                'result_preview': 'sum | 10.00 CNY',
            }],
        )
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_USER,
            content='第二次',
            position=2,
        )
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_ASSISTANT,
            content='',
            position=3,
            generation_status=ChatMessage.STATUS_GENERATING,
        )

        records = collect_prior_query_records(session)
        assert len(records) == 1
        assert records[0]['bql'] == 'SELECT 1'


class TestPriorQueryValidation:
    def test_validate_reply_numbers_accepts_amount_from_prior_queries(self):
        prior = [{'bql': 'SELECT 1', 'result_preview': 'sum | 5000.00 CNY'}]
        merged = query_records_from_dicts(prior)
        result = validate_reply_numbers('上月支出 **5000.00** 元。', merged)
        assert result.ok is True

    def test_validate_reply_numbers_rejects_when_amount_missing_everywhere(self):
        prior = [{'bql': 'SELECT 1', 'result_preview': 'sum | 10.00 CNY'}]
        merged = query_records_from_dicts(prior)
        result = validate_reply_numbers('支出 **999.00** 元。', merged)
        assert result.ok is False
