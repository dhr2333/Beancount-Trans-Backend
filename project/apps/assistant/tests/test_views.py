import pytest
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from project.apps.assistant.models import SharedLedgerBinding
from project.apps.assistant.services.api_key_resolver import DEFAULT_ASSISTANT_MODEL
from project.apps.assistant.tests.conftest import SAMPLE_BEAN
from project.apps.assistant.tests.test_assistant_service import (
    _clear_assistant_provider,
    _make_text_stream,
    _make_tool_call_stream,
)
from project.apps.authentication.models import PersonalAccessToken
from project.apps.translate.models import FormatConfig

User = get_user_model()


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def owner_user(db):
    return User.objects.create_user(
        username='owneruser',
        email='owner@example.com',
        password='testpass123',
    )


@pytest.fixture
def api_client_owner(owner_user):
    client = APIClient()
    client.force_authenticate(user=owner_user)
    return client


@pytest.mark.django_db
class TestAssistantAPI:
    def test_status_endpoint(self, api_client, user, bean_file):
        with override_settings(
            ASSISTANT_DEEPSEEK_API_KEY='platform-sk',
            ASSISTANT_MODEL=DEFAULT_ASSISTANT_MODEL,
        ):
            response = api_client.get(reverse('assistant-status'))

        assert response.status_code == 200
        assert response.data['ledger_exists'] is True
        assert response.data['api_key_configured'] is True
        assert response.data['assistant_model'] == DEFAULT_ASSISTANT_MODEL
        assert response.data['deep_think_supported'] is True
        assert 'reference_date' in response.data

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    def test_chat_without_key_returns_400(self, api_client, user, bean_file):
        config = FormatConfig.get_user_config(user)
        _clear_assistant_provider(config)

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
        _clear_assistant_provider(config)

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

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test', ASSISTANT_MODEL='deepseek-v4-flash')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_chat_stream_with_deep_think(self, mock_openai_cls, api_client, user, bean_file):
        config = FormatConfig.get_user_config(user)
        _clear_assistant_provider(config)

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_text_stream('你好。'),
        ]

        response = api_client.post(
            reverse('assistant-chat-stream'),
            {
                'messages': [{'role': 'user', 'content': '你好'}],
                'deep_think': True,
            },
            format='json',
            HTTP_ACCEPT='text/event-stream',
        )

        assert response.status_code == 200
        body = b''.join(response.streaming_content).decode('utf-8')
        assert 'event: done' in body
        first_kwargs = mock_client.chat.completions.create.call_args_list[0].kwargs
        assert first_kwargs['model'] == 'deepseek-v4-flash'
        assert first_kwargs['extra_body'] == {'thinking': {'type': 'enabled'}}

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk')
    def test_test_key_empty_allows_copilot_not_parse(self, api_client):
        response = api_client.post(
            reverse('assistant-test-key'),
            {'api_key': '', 'base_url': '', 'model': ''},
            format='json',
        )
        assert response.status_code == 200
        assert response.data['ok'] is True
        assert response.data['copilot_available'] is True
        assert response.data['parse_available'] is False

    @patch('project.apps.assistant.services.key_tester.probe_llm_connection')
    def test_test_key_filled_enables_parse(self, mock_probe, api_client):
        response = api_client.post(
            reverse('assistant-test-key'),
            {
                'api_key': 'user-sk-test',
                'base_url': 'https://api.deepseek.com',
                'model': 'deepseek-v4-flash',
            },
            format='json',
        )
        mock_probe.assert_called_once()
        assert response.status_code == 200
        assert response.data['ok'] is True
        assert response.data['parse_available'] is True

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.views.AssistantService')
    def test_chat_stream_without_done_emits_error(self, mock_service_cls, api_client, user, bean_file):
        from project.apps.assistant.services.assistant_service import StreamEvent

        config = FormatConfig.get_user_config(user)
        _clear_assistant_provider(config)

        mock_service = mock_service_cls.return_value
        mock_service._iter_chat_events.return_value = iter([
            StreamEvent('delta', {'content': '部分回复'}),
        ])

        response = api_client.post(
            reverse('assistant-chat-stream'),
            {'messages': [{'role': 'user', 'content': '你好'}]},
            format='json',
            HTTP_ACCEPT='text/event-stream',
        )

        assert response.status_code == 200
        body = b''.join(response.streaming_content).decode('utf-8')
        assert 'event: error' in body
        assert '助手响应未完成' in body


@pytest.mark.django_db
class TestSharedLedgerAPI:
    list_url = 'assistant-shared-ledger-list'
    detail_url = 'assistant-shared-ledger-detail'

    def _post_binding(self, client, owner, label=''):
        _token, raw_token = PersonalAccessToken.issue(owner, '分享账本')
        payload = {'token': raw_token}
        if label:
            payload['label'] = label
        return client.post(reverse(self.list_url), payload, format='json')

    def test_list_returns_only_current_user_bindings(
        self, api_client, owner_user, api_client_owner,
    ):
        created = self._post_binding(api_client, owner_user)
        assert created.status_code == 201

        listing = api_client.get(reverse(self.list_url))
        assert listing.status_code == 200
        assert len(listing.data) == 1
        assert listing.data[0]['owner_username'] == owner_user.username
        assert 'usable' in listing.data[0]

        # 另一个用户看不到该绑定
        other = api_client_owner.get(reverse(self.list_url))
        assert other.status_code == 200
        assert other.data == []

    def test_create_with_valid_token(self, api_client, owner_user):
        response = self._post_binding(api_client, owner_user, label='家庭')

        assert response.status_code == 201
        assert response.data['owner_username'] == owner_user.username
        assert response.data['label'] == '家庭'
        assert response.data['usable'] is True

        listing = api_client.get(reverse(self.list_url))
        assert [row['id'] for row in listing.data] == [response.data['id']]

    def test_create_with_invalid_token_returns_400(self, api_client):
        response = api_client.post(
            reverse(self.list_url), {'token': 'not-a-token'}, format='json'
        )

        assert response.status_code == 400
        assert '令牌无效' in response.data['detail']

    def test_create_with_own_token_returns_400(self, api_client, user):
        _token, raw_token = PersonalAccessToken.issue(user, '自己的令牌')

        response = api_client.post(
            reverse(self.list_url), {'token': raw_token}, format='json'
        )

        assert response.status_code == 400
        assert '自己' in response.data['detail']

    def test_create_without_scope_returns_400(self, api_client, owner_user):
        _token, raw_token = PersonalAccessToken.issue(
            owner_user, '无权限令牌', scopes='other'
        )

        response = api_client.post(
            reverse(self.list_url), {'token': raw_token}, format='json'
        )

        assert response.status_code == 400
        assert '权限' in response.data['detail']

    def test_create_duplicate_owner_returns_400(self, api_client, owner_user):
        first = self._post_binding(api_client, owner_user)
        assert first.status_code == 201

        second = self._post_binding(api_client, owner_user)

        assert second.status_code == 400
        assert '重复' in second.data['detail']
        assert len(api_client.get(reverse(self.list_url)).data) == 1

    def test_delete_own_binding(self, api_client, owner_user):
        created = self._post_binding(api_client, owner_user)
        binding_id = created.data['id']

        response = api_client.delete(
            reverse(self.detail_url, args=[binding_id])
        )

        assert response.status_code == 204
        assert api_client.get(reverse(self.list_url)).data == []

    def test_delete_other_users_binding_returns_404(self, api_client, user, owner_user):
        token, _raw_token = PersonalAccessToken.issue(user, '我的令牌')
        binding = SharedLedgerBinding.objects.create(
            recipient=owner_user, token=token
        )

        response = api_client.delete(
            reverse(self.detail_url, args=[binding.id])
        )

        assert response.status_code == 404
        assert SharedLedgerBinding.objects.filter(id=binding.id).exists()

    def test_unauthenticated_returns_401(self):
        client = APIClient()

        response = client.get(reverse(self.list_url))

        assert response.status_code == 401

    @override_settings(ASSISTANT_MAX_SHARED_LEDGERS=1)
    def test_chat_rejects_too_many_shared_binding_ids(self, api_client):
        response = api_client.post(
            reverse('assistant-chat'),
            {
                'messages': [{'role': 'user', 'content': '你好'}],
                'shared_binding_ids': [1, 2],
            },
            format='json',
        )

        assert response.status_code == 400
        assert 'shared_binding_ids' in response.data
        assert '最多纳入' in str(response.data['shared_binding_ids'])

    @override_settings(ASSISTANT_MAX_SHARED_LEDGERS=1)
    def test_chat_stream_rejects_too_many_shared_binding_ids(self, api_client):
        response = api_client.post(
            reverse('assistant-chat-stream'),
            {
                'messages': [{'role': 'user', 'content': '你好'}],
                'shared_binding_ids': [1, 2],
            },
            format='json',
            HTTP_ACCEPT='text/event-stream',
        )

        assert response.status_code == 400
        assert 'shared_binding_ids' in response.data
        assert '最多纳入' in str(response.data['shared_binding_ids'])

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_chat_without_shared_binding_ids_still_ok(
        self, mock_openai_cls, api_client, user, bean_file,
    ):
        config = FormatConfig.get_user_config(user)
        _clear_assistant_provider(config)

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_text_stream('你好。'),
        ]

        response = api_client.post(
            reverse('assistant-chat'),
            {'messages': [{'role': 'user', 'content': '你好'}]},
            format='json',
        )

        assert response.status_code == 200
        assert '你好' in response.data['reply']

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.services.assistant_service.OpenAI')
    def test_chat_stream_with_shared_binding_without_own_ledger(
        self, mock_openai_cls, api_client, user, owner_user,
        tmp_path, settings, monkeypatch,
    ):
        # 仅 owner 拥有账本文件；recipient（user）没有自己的账本
        assets_dir = tmp_path / owner_user.username
        assets_dir.mkdir(parents=True)
        (assets_dir / 'main.bean').write_text(SAMPLE_BEAN, encoding='utf-8')
        monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', tmp_path)

        config = FormatConfig.get_user_config(user)
        _clear_assistant_provider(config)

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _make_text_stream('你好。'),
        ]

        created = self._post_binding(api_client, owner_user)
        assert created.status_code == 201
        binding_id = created.data['id']

        # 有可用的共享账本绑定：不应触发「无账本」预检 404
        response = api_client.post(
            reverse('assistant-chat-stream'),
            {
                'messages': [{'role': 'user', 'content': '你好'}],
                'shared_binding_ids': [binding_id],
            },
            format='json',
            HTTP_ACCEPT='text/event-stream',
        )
        assert response.status_code != 404
        body = b''.join(response.streaming_content).decode('utf-8')
        assert '尚未创建任何可访问的账本' not in body

        # 对照：不带共享账本 id 时，预检仍应返回 404
        no_binding = api_client.post(
            reverse('assistant-chat-stream'),
            {
                'messages': [{'role': 'user', 'content': '你好'}],
                'shared_binding_ids': [],
            },
            format='json',
            HTTP_ACCEPT='text/event-stream',
        )
        assert no_binding.status_code == 404
        assert '尚未创建任何可访问的账本' in no_binding.data['detail']
