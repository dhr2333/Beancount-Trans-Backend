import uuid

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from project.apps.assistant.models import AssistantFeedback


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def message_id():
    return uuid.uuid4()


@pytest.fixture
def feedback_payload(message_id):
    return {
        'message_id': str(message_id),
        'rating': 'like',
        'user_message': '本月餐饮花了多少？',
        'assistant_reply': '本月餐饮支出 50 元。',
        'queries': [{'bql': 'SELECT 1', 'result_preview': 'ok'}],
    }


@pytest.mark.django_db
class TestAssistantFeedbackAPI:
    def test_submit_like_feedback(self, api_client, user, feedback_payload):
        response = api_client.post(
            reverse('assistant-feedback'),
            feedback_payload,
            format='json',
        )

        assert response.status_code == 200
        assert response.data['rating'] == 'like'
        assert AssistantFeedback.objects.filter(user=user).count() == 1

    def test_submit_dislike_with_comment(self, api_client, user, feedback_payload):
        feedback_payload['rating'] = 'dislike'
        feedback_payload['comment'] = '数字不准确'

        response = api_client.post(
            reverse('assistant-feedback'),
            feedback_payload,
            format='json',
        )

        assert response.status_code == 200
        record = AssistantFeedback.objects.get(user=user)
        assert record.rating == 'dislike'
        assert record.comment == '数字不准确'

    def test_update_feedback_rating(self, api_client, user, feedback_payload):
        api_client.post(reverse('assistant-feedback'), feedback_payload, format='json')

        feedback_payload['rating'] = 'dislike'
        feedback_payload['comment'] = '回答太简略'
        response = api_client.post(
            reverse('assistant-feedback'),
            feedback_payload,
            format='json',
        )

        assert response.status_code == 200
        assert AssistantFeedback.objects.filter(user=user).count() == 1
        record = AssistantFeedback.objects.get(user=user)
        assert record.rating == 'dislike'
        assert record.comment == '回答太简略'

    def test_cancel_feedback(self, api_client, user, feedback_payload):
        api_client.post(reverse('assistant-feedback'), feedback_payload, format='json')

        response = api_client.post(
            reverse('assistant-feedback'),
            {
                **feedback_payload,
                'rating': None,
            },
            format='json',
        )

        assert response.status_code == 200
        assert response.data['rating'] is None
        assert AssistantFeedback.objects.filter(user=user).count() == 0

    def test_feedback_requires_auth(self, feedback_payload):
        client = APIClient()
        response = client.post(
            reverse('assistant-feedback'),
            feedback_payload,
            format='json',
        )
        assert response.status_code == 401
