import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from project.apps.translate.models import FormatConfig


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
