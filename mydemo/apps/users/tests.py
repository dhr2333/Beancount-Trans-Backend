from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.views import TokenObtainPairView
from users.models import User
from users.views import CreateUserView


class LoginViewTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username='test',
            password='test'
        )

    def test_get_token(self):
        request = self.factory.post('/token/', {'username': 'test', 'password': 'test'})
        response = TokenObtainPairView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['access'], str(response.data['access']))
        self.assertEqual(response.data['refresh'], str(response.data['refresh']))


class CreateUserViewTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username='test',
            password='test'
        )

    def test_create_user(self):
        request_token = self.factory.post('/token/', {'username': 'test', 'password': 'test'})
        response_token = TokenObtainPairView.as_view()(request_token)
        token = response_token.data['access']

        request = self.factory.post('/user/create/', {'username': 'test1', 'password': 'test1', 'password2': 'test1',
                                                      'mobile': '12345678910'}, HTTP_AUTHORIZATION='Bearer ' + token)
        response = CreateUserView.as_view()(request)
        self.assertEqual(response.status_code, 201)


class UserViewSetTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username='test',
            password='test'
        )

    def test_get_user(self):
        request_token = self.factory.post('/token/', {'username': 'test', 'password': 'test'})
        response_token = TokenObtainPairView.as_view()(request_token)
        token = response_token.data['access']
        response = self.client.get('/users/', HTTP_AUTHORIZATION='Bearer ' + token)
        self.assertEqual(response.status_code, 200)
