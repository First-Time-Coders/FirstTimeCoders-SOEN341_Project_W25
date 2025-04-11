from unittest.mock import patch, ANY, MagicMock

from django.contrib.auth.models import User
from django.test import Client, TestCase, RequestFactory
from django.urls import reverse
from gotrue.errors import AuthApiError


class LoginTestCases(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('login')

    def test_login_view_success(self):
        response = self.client.post(self.login_url, {
            'email': 'julianetmegamanzero@gmail.com',
            'password': '123456'
        })

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/api/dashboard-admin/')

    def test_login_view_failure(self):
        response = self.client.post(self.login_url, {
            'email': 'fake@gmail.com',
            'password': '123456'
        })

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/api/login/')

