import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestFavaStaticMode:
    @override_settings(
        FAVA_DEPLOY_MODE='static',
        FAVA_STATIC_USER_MAP={'staticuser': 'http://localhost:5999'},
    )
    def test_get_returns_json_url(self):
        user = User.objects.create_user(username='staticuser', password='x')
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/fava/')
        assert response.status_code == 200
        assert response.data['url'] == 'http://localhost:5999'
        assert response.data['deploy_mode'] == 'static'

    @override_settings(
        FAVA_DEPLOY_MODE='static',
        FAVA_STATIC_USER_MAP={'other': 'http://localhost:1'},
    )
    def test_get_404_when_not_in_map(self):
        user = User.objects.create_user(username='staticuser', password='x')
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/fava/')
        assert response.status_code == 404
        assert response.data.get('code') == 'FAVA_STATIC_NOT_CONFIGURED'

    @override_settings(FAVA_DEPLOY_MODE='static', FAVA_STATIC_USER_MAP={})
    def test_stop_noop(self):
        user = User.objects.create_user(username='u', password='x')
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/fava/stop/')
        assert response.status_code == 200
        assert response.data.get('stopped_count') == 0
