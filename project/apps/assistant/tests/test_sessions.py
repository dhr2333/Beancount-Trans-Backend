import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from project.apps.assistant.models import ChatMessage, ChatSession
from project.apps.assistant.services.api_key_resolver import DEFAULT_ASSISTANT_MODEL
from project.apps.assistant.tests.test_assistant_service import (
    _clear_assistant_provider,
    _make_text_stream,
    _make_tool_call_stream,
    _with_guard_retry,
)
from project.apps.translate.models import FormatConfig


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def other_user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        username='otherassistant',
        email='other@example.com',
        password='testpass123',
    )


def _parse_sse_events(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.split('\n\n'):
        block = block.strip()
        if not block:
            continue
        event_type = 'message'
        data = None
        for line in block.split('\n'):
            if line.startswith('event: '):
                event_type = line[7:].strip()
            elif line.startswith('data: '):
                data = json.loads(line[6:])
        if data is not None:
            events.append((event_type, data))
    return events


@pytest.mark.django_db
class TestAssistantSessions:
    def test_list_sessions_empty(self, api_client, user, bean_file):
        response = api_client.get(reverse('assistant-session-list'))
        assert response.status_code == 200
        assert response.data == []

    def test_list_sessions_isolated_by_user(self, api_client, user, other_user, bean_file):
        ChatSession.objects.create(user=user, title='我的会话')
        ChatSession.objects.create(user=other_user, title='他人会话')

        response = api_client.get(reverse('assistant-session-list'))
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['title'] == '我的会话'

    def test_retrieve_session_with_messages(self, api_client, user, bean_file):
        session = ChatSession.objects.create(user=user, title='测试会话')
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_USER,
            content='你好',
            position=0,
        )
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_ASSISTANT,
            content='你好，我能帮你什么？',
            position=1,
        )

        response = api_client.get(
            reverse('assistant-session-detail', kwargs={'id': session.id}),
        )
        assert response.status_code == 200
        assert response.data['title'] == '测试会话'
        assert len(response.data['messages']) == 2
        assert response.data['messages'][0]['role'] == 'user'

    def test_retrieve_other_user_session_returns_404(self, api_client, user, other_user, bean_file):
        session = ChatSession.objects.create(user=other_user, title='他人会话')
        response = api_client.get(
            reverse('assistant-session-detail', kwargs={'id': session.id}),
        )
        assert response.status_code == 404

    def test_patch_title_locks_session(self, api_client, user, bean_file):
        session = ChatSession.objects.create(user=user, title='旧标题')
        response = api_client.patch(
            reverse('assistant-session-detail', kwargs={'id': session.id}),
            {'title': '新标题'},
            format='json',
        )
        assert response.status_code == 200
        session.refresh_from_db()
        assert session.title == '新标题'
        assert session.title_locked is True

    def test_delete_session(self, api_client, user, bean_file):
        session = ChatSession.objects.create(user=user, title='待删除')
        response = api_client.delete(
            reverse('assistant-session-detail', kwargs={'id': session.id}),
        )
        assert response.status_code == 204
        assert not ChatSession.objects.filter(id=session.id).exists()

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_stream_creates_session_and_persists_messages(
        self,
        mock_openai_cls,
        api_client,
        user,
        bean_file,
    ):
        config = FormatConfig.get_user_config(user)
        _clear_assistant_provider(config)

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = _with_guard_retry(
            _make_tool_call_stream('run_bql', '{"query": "SELECT account LIMIT 1"}'),
            _make_text_stream('已根据查询结果汇总。'),
        )

        response = api_client.post(
            reverse('assistant-chat-stream'),
            {'content': '本月餐饮花了多少？', 'deep_think': False},
            format='json',
            HTTP_ACCEPT='text/event-stream',
        )

        assert response.status_code == 200
        body = b''.join(response.streaming_content).decode('utf-8')
        events = _parse_sse_events(body)
        event_types = [name for name, _ in events]
        assert 'session' in event_types
        assert 'done' in event_types

        session_event = next(data for name, data in events if name == 'session')
        done_event = next(data for name, data in events if name == 'done')

        session = ChatSession.objects.get(id=session_event['id'])
        assert session.user_id == user.id
        assert session.title == '本月餐饮花了多少？'
        assert session.messages.count() == 2
        assert done_event['assistant_message_id']
        assert done_event['user_message_id'] == session_event['user_message_id']

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_stream_continue_session_uses_db_history(
        self,
        mock_openai_cls,
        api_client,
        user,
        bean_file,
    ):
        config = FormatConfig.get_user_config(user)
        _clear_assistant_provider(config)

        session = ChatSession.objects.create(user=user, title='续聊')
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_USER,
            content='第一次问题',
            position=0,
        )
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_ASSISTANT,
            content='第一次回答',
            position=1,
        )

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_text_stream('第二次回答')

        response = api_client.post(
            reverse('assistant-chat-stream'),
            {
                'session_id': str(session.id),
                'content': '第二次问题',
                'deep_think': False,
            },
            format='json',
            HTTP_ACCEPT='text/event-stream',
        )

        assert response.status_code == 200
        b''.join(response.streaming_content)

        assert session.messages.count() == 4
        llm_messages = mock_client.chat.completions.create.call_args.kwargs['messages']
        user_contents = [msg['content'] for msg in llm_messages if msg['role'] == 'user']
        assert '第一次问题' in user_contents
        assert '第二次问题' in user_contents

    def test_stream_without_key_does_not_create_session(self, api_client, user, bean_file):
        config = FormatConfig.get_user_config(user)
        _clear_assistant_provider(config)

        with override_settings(ASSISTANT_DEEPSEEK_API_KEY=''):
            response = api_client.post(
                reverse('assistant-chat-stream'),
                {'content': '你好'},
                format='json',
            )

        assert response.status_code == 400
        assert ChatSession.objects.count() == 0

    def test_list_sessions_search(self, api_client, user, bean_file):
        ChatSession.objects.create(user=user, title='餐饮分析')
        ChatSession.objects.create(user=user, title='旅行预算')

        response = api_client.get(
            reverse('assistant-session-list'),
            {'search': '餐饮'},
        )
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['title'] == '餐饮分析'
