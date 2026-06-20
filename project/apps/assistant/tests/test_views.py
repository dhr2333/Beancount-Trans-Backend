import pytest
from unittest.mock import MagicMock, patch

from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from project.apps.translate.models import FormatConfig
from project.apps.assistant.tests.test_assistant_service import (
    _make_text_stream,
    _make_tool_call_stream,
)


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestAssistantAPI:
    def test_status_endpoint(self, api_client, user, bean_file):
        with override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk'):
            response = api_client.get(reverse('assistant-status'))

        assert response.status_code == 200
        assert response.data['ledger_exists'] is True
        assert response.data['api_key_configured'] is True
        assert response.data['api_key_source'] == 'platform'
        assert 'reference_date' in response.data

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    def test_chat_without_key_returns_400(self, api_client, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        with override_settings(ASSISTANT_DEEPSEEK_API_KEY=''):
            response = api_client.post(
                reverse('assistant-chat'),
                {'messages': [{'role': 'user', 'content': '你好'}]},
                format='json',
            )
        assert response.status_code == 400

    def test_chat_requires_auth(self, bean_file):
        client = APIClient()
        response = client.get(reverse('assistant-status'))
        assert response.status_code == 401

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_chat_stream_endpoint_returns_sse(self, mock_openai_cls, api_client, user, bean_file):
        config = FormatConfig.get_user_config(user)
        config.deepseek_apikey = ''
        config.save()

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_tool_call_stream('run_bql', '{"query": "SELECT account LIMIT 1"}'),
            _make_text_stream('你好。'),
        ]

        response = api_client.post(
            reverse('assistant-chat-stream'),
            {'messages': [{'role': 'user', 'content': '你好'}]},
            format='json',
            HTTP_ACCEPT='text/event-stream',
        )

        assert response.status_code == 200
        assert response['Content-Type'].startswith('text/event-stream')
        body = b''.join(response.streaming_content).decode('utf-8')
        assert 'event: done' in body
        assert 'event: delta' in body
        assert 'event: tool_end' in body
