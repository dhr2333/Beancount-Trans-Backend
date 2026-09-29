import pytest
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from project.apps.assistant.models import ChatSession, SharedLedgerBinding
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


@pytest.fixture(autouse=True)
def _reset_rate_limit_cache():
    """避免用例间共享 assistant_chat 限流计数（20/hour）导致误报 429。"""
    cache.clear()
    yield
    cache.clear()


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
        assert response.data['has_usable_shared_ledger'] is False
        assert response.data['api_key_configured'] is True
        assert response.data['assistant_model'] == DEFAULT_ASSISTANT_MODEL
        assert response.data['deep_think_supported'] is True
        assert 'reference_date' in response.data

    def test_status_has_usable_shared_ledger_false_without_binding(
        self, api_client, user, tmp_path, settings, monkeypatch,
    ):
        monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', tmp_path)

        with override_settings(
            ASSISTANT_DEEPSEEK_API_KEY='platform-sk',
            ASSISTANT_MODEL=DEFAULT_ASSISTANT_MODEL,
        ):
            response = api_client.get(reverse('assistant-status'))

        assert response.status_code == 200
        assert response.data['ledger_exists'] is False
        assert response.data['has_usable_shared_ledger'] is False

    def test_status_has_usable_shared_ledger_true_without_own_ledger(
        self, api_client, user, owner_user, tmp_path, settings, monkeypatch,
    ):
        monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', tmp_path)
        _token, raw_token = PersonalAccessToken.issue(owner_user, '分享账本')
        created = api_client.post(
            reverse('assistant-shared-ledger-list'),
            {'token': raw_token},
            format='json',
        )
        assert created.status_code == 201

        with override_settings(
            ASSISTANT_DEEPSEEK_API_KEY='platform-sk',
            ASSISTANT_MODEL=DEFAULT_ASSISTANT_MODEL,
        ):
            response = api_client.get(reverse('assistant-status'))

        assert response.status_code == 200
        # ledger_exists 仍只反映本人账本
        assert response.data['ledger_exists'] is False
        assert response.data['has_usable_shared_ledger'] is True

    def test_status_has_usable_shared_ledger_false_when_token_revoked(
        self, api_client, user, owner_user, tmp_path, settings, monkeypatch,
    ):
        monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', tmp_path)
        token, raw_token = PersonalAccessToken.issue(owner_user, '分享账本')
        api_client.post(
            reverse('assistant-shared-ledger-list'),
            {'token': raw_token},
            format='json',
        )
        token.revoked_at = timezone.now()
        token.save(update_fields=['revoked_at'])

        with override_settings(
            ASSISTANT_DEEPSEEK_API_KEY='platform-sk',
            ASSISTANT_MODEL=DEFAULT_ASSISTANT_MODEL,
        ):
            response = api_client.get(reverse('assistant-status'))

        assert response.status_code == 200
        assert response.data['has_usable_shared_ledger'] is False

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

    def _post_binding(self, client, owner, aliases=None):
        _token, raw_token = PersonalAccessToken.issue(owner, '分享账本')
        payload = {'token': raw_token}
        if aliases is not None:
            payload['aliases'] = aliases
        return client.post(
            reverse(self.list_url),
            payload,
            format='json',
        )

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
        response = self._post_binding(api_client, owner_user, aliases=['家庭'])

        assert response.status_code == 201
        assert response.data['owner_username'] == owner_user.username
        assert response.data['aliases'] == ['家庭']
        assert response.data['usable'] is True

        listing = api_client.get(reverse(self.list_url))
        assert [row['id'] for row in listing.data] == [response.data['id']]

    def test_create_with_invalid_token_returns_400(self, api_client):
        response = api_client.post(
            reverse(self.list_url),
            {'token': 'not-a-token', 'aliases': ['家庭账本']},
            format='json',
        )

        assert response.status_code == 400
        assert '令牌无效' in response.data['detail']

    def test_create_with_own_token_returns_400(self, api_client, user):
        _token, raw_token = PersonalAccessToken.issue(user, '自己的令牌')

        response = api_client.post(
            reverse(self.list_url),
            {'token': raw_token, 'aliases': ['家庭账本']},
            format='json',
        )

        assert response.status_code == 400
        assert '自己' in response.data['detail']

    def test_create_without_scope_returns_400(self, api_client, owner_user):
        _token, raw_token = PersonalAccessToken.issue(
            owner_user, '无权限令牌', scopes='other'
        )

        response = api_client.post(
            reverse(self.list_url),
            {'token': raw_token, 'aliases': ['家庭账本']},
            format='json',
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

    def test_patch_updates_aliases(self, api_client, owner_user):
        created = self._post_binding(api_client, owner_user, aliases=['旧别名'])

        response = api_client.patch(
            reverse(self.detail_url, args=[created.data['id']]),
            {'aliases': ['新别名', '别名二']},
            format='json',
        )

        assert response.status_code == 200
        assert response.data['aliases'] == ['新别名', '别名二']
        assert api_client.get(reverse(self.list_url)).data[0]['aliases'] == ['新别名', '别名二']

    def test_patch_can_clear_aliases(self, api_client, owner_user):
        created = self._post_binding(api_client, owner_user, aliases=['家庭账本'])

        response = api_client.patch(
            reverse(self.detail_url, args=[created.data['id']]),
            {'aliases': []},
            format='json',
        )

        assert response.status_code == 200
        assert response.data['aliases'] == []

    def test_patch_requires_aliases_field(self, api_client, owner_user):
        created = self._post_binding(api_client, owner_user, aliases=['家庭账本'])

        response = api_client.patch(
            reverse(self.detail_url, args=[created.data['id']]),
            {},
            format='json',
        )

        assert response.status_code == 400
        assert 'aliases' in response.data

    def test_patch_rejects_alias_used_by_other_binding(self, api_client, owner_user):
        first = self._post_binding(api_client, owner_user, aliases=['家庭账本'])
        other_owner = User.objects.create_user(
            username='secondowner', password='testpass123'
        )
        second = self._post_binding(api_client, other_owner, aliases=['他账本'])

        response = api_client.patch(
            reverse(self.detail_url, args=[second.data['id']]),
            {'aliases': ['家庭账本']},
            format='json',
        )

        assert response.status_code == 400
        assert '已被其他共享账本使用' in response.data['detail']
        assert first.data['id'] != second.data['id']

    def test_patch_rejects_reserved_alias(self, api_client, owner_user):
        created = self._post_binding(api_client, owner_user, aliases=['家庭账本'])

        response = api_client.patch(
            reverse(self.detail_url, args=[created.data['id']]),
            {'aliases': ['self']},
            format='json',
        )

        assert response.status_code == 400
        assert '保留值' in response.data['detail']

    def test_patch_other_users_binding_returns_404(self, api_client, user, owner_user):
        token, _raw_token = PersonalAccessToken.issue(user, '我的令牌')
        binding = SharedLedgerBinding.objects.create(
            recipient=owner_user, token=token, aliases=['家庭账本']
        )

        response = api_client.patch(
            reverse(self.detail_url, args=[binding.id]),
            {'aliases': ['新别名']},
            format='json',
        )

        assert response.status_code == 404
        binding.refresh_from_db()
        assert binding.aliases == ['家庭账本']

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

    def test_create_without_aliases_succeeds(self, api_client, owner_user):
        _token, raw_token = PersonalAccessToken.issue(owner_user, '分享账本')

        response = api_client.post(
            reverse(self.list_url),
            {'token': raw_token},
            format='json',
        )

        assert response.status_code == 201
        assert response.data['aliases'] == []

    def test_create_with_blank_aliases_stores_empty(self, api_client, owner_user):
        _token, raw_token = PersonalAccessToken.issue(owner_user, '分享账本')

        response = api_client.post(
            reverse(self.list_url),
            {'token': raw_token, 'aliases': ['', '   ']},
            format='json',
        )

        assert response.status_code == 201
        assert response.data['aliases'] == []

    def test_create_with_reserved_alias_returns_400(self, api_client, owner_user):
        response = self._post_binding(api_client, owner_user, aliases=['self'])

        assert response.status_code == 400
        assert '别名不能使用保留值 self' in response.data['detail']

    def test_create_with_overlong_alias_returns_400(self, api_client, owner_user):
        response = self._post_binding(api_client, owner_user, aliases=['账本' * 40])

        assert response.status_code == 400
        assert 'aliases' in response.data

    def test_create_duplicate_alias_for_other_owner_returns_400(
        self, api_client, owner_user,
    ):
        first = self._post_binding(api_client, owner_user, aliases=['家庭账本'])
        assert first.status_code == 201

        other = User.objects.create_user(username='otheruser', password='x')
        second = self._post_binding(api_client, other, aliases=['家庭账本'])

        assert second.status_code == 400
        assert '已被其他共享账本使用' in second.data['detail']

    def test_list_exposes_aliases_without_label(self, api_client, owner_user):
        created = self._post_binding(api_client, owner_user, aliases=['家庭账本'])
        assert created.status_code == 201

        listing = api_client.get(reverse(self.list_url))

        assert listing.status_code == 200
        assert listing.data[0]['aliases'] == ['家庭账本']
        assert 'label' not in listing.data[0]

    def test_create_echoes_aliases_without_label(self, api_client, owner_user):
        response = self._post_binding(api_client, owner_user, aliases=['老婆的账本', '老婆'])

        assert response.status_code == 201
        assert response.data['aliases'] == ['老婆的账本', '老婆']
        assert 'label' not in response.data

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.tasks.AssistantService._iter_chat_events')
    def test_stream_without_binding_ids_records_all_usable_newest_first(
        self, mock_iter, api_client, user, bean_file, owner_user,
    ):
        config = FormatConfig.get_user_config(user)
        _clear_assistant_provider(config)
        mock_iter.return_value = iter([])

        first = self._post_binding(api_client, owner_user)
        other = User.objects.create_user(username='streamother1', password='x')
        second = self._post_binding(api_client, other)
        assert first.status_code == 201
        assert second.status_code == 201
        first_id = first.data['id']
        second_id = second.data['id']

        response = api_client.post(
            reverse('assistant-chat-stream'),
            {'content': '你好'},
            format='json',
            HTTP_ACCEPT='text/event-stream',
        )

        # 缺省即全部可用：不因未传字段而 404
        assert response.status_code != 404
        b''.join(response.streaming_content)
        session = ChatSession.objects.get(user=user)
        assert session.shared_binding_ids == [second_id, first_id]

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.tasks.AssistantService._iter_chat_events')
    def test_stream_empty_ids_overrides_stored_session_ids(
        self, mock_iter, api_client, user, bean_file, owner_user,
    ):
        config = FormatConfig.get_user_config(user)
        _clear_assistant_provider(config)
        mock_iter.return_value = iter([])

        created = self._post_binding(api_client, owner_user)
        binding_id = created.data['id']
        session = ChatSession.objects.create(
            user=user, title='旧会话', shared_binding_ids=[binding_id],
        )

        response = api_client.post(
            reverse('assistant-chat-stream'),
            {
                'session_id': str(session.id),
                'content': '你好',
                'shared_binding_ids': [],
            },
            format='json',
            HTTP_ACCEPT='text/event-stream',
        )

        assert response.status_code == 200
        b''.join(response.streaming_content)
        session.refresh_from_db()
        # 显式 [] 表示仅本人账本，不得回退到会话旧值
        assert session.shared_binding_ids == []

    @override_settings(ASSISTANT_DEEPSEEK_API_KEY='platform-sk-test')
    @patch('project.apps.assistant.tasks.AssistantService._iter_chat_events')
    def test_stream_subset_ids_records_subset(
        self, mock_iter, api_client, user, bean_file, owner_user,
    ):
        config = FormatConfig.get_user_config(user)
        _clear_assistant_provider(config)
        mock_iter.return_value = iter([])

        first = self._post_binding(api_client, owner_user)
        other = User.objects.create_user(username='streamother2', password='x')
        self._post_binding(api_client, other)
        first_id = first.data['id']

        response = api_client.post(
            reverse('assistant-chat-stream'),
            {'content': '你好', 'shared_binding_ids': [first_id]},
            format='json',
            HTTP_ACCEPT='text/event-stream',
        )

        assert response.status_code != 404
        b''.join(response.streaming_content)
        session = ChatSession.objects.get(user=user)
        assert session.shared_binding_ids == [first_id]
