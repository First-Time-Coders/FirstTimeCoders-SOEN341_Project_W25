from unittest.mock import patch, ANY, MagicMock

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from gotrue.errors import AuthApiError
import datetime


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

class RegisterTestCases(TestCase):
    def setUp(self):
        self.client = Client()

    @patch('api.views.supabase_client')
    @patch('api.views.bcrypt')
    def test_register_view_success(self, mock_bcrypt, mock_supabase):
        mock_bcrypt.gensalt.return_value = b'salt'
        mock_bcrypt.hashpw.return_value = b'hashedpass'
        self.register_url = '/api/register/'

        mock_supabase.auth.sign_up.return_value.user.id = 'uuid123'
        mock_supabase.table.return_value.insert.return_value.execute.return_value = {'data': 'ok'}

        response = self.client.post(self.register_url, {
            'email': 'testEmail@example.com',
            'username': 'user',
            'password': '123456',
            'first_name': 'Julian',
            'last_name': 'Valencia',
            'gender': 'M',
            'role': 'admin'
        })

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/api/login/')

    @patch('api.views.supabase_client.auth.sign_up')
    @patch('api.views.messages')
    def test_register_view_password_length_error(self, mock_messages, mock_sign_up):
        self.register_url = '/api/register/'

        response = self.client.post(self.register_url, {
            'email': 'testEmail@example.com',
            'username': 'user',
            'password': '123',
            'first_name': 'Julian',
            'last_name': 'Valencia',
            'gender': 'M',
            'role': 'admin'
        })

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/api/register/')

class ChannelTestCases(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.session['user_uuid'] = 'test-user-id'
        self.client.session.save()
        self.create_url = reverse('create-channel')
        self.delete_url = lambda channel_id: reverse('delete-channel', args=[channel_id])

    @patch('api.views.supabase_client.table')
    def test_create_channel_success(self, mock_table):
        session = self.client.session
        session['user_uuid'] = '984735473-23432-438828-1284'
        session['access_token'] = 'dummy-token'
        session.save()

        mock_insert = MagicMock()
        mock_table.return_value.insert.return_value = mock_insert
        mock_insert.execute.return_value = MagicMock()

        response = self.client.post(self.create_url, {
            'name': 'Test Channel',
            'description': 'Test Description'
        })

        self.assertEqual(response.status_code, 302)

    @patch('api.views.supabase_client.table')
    def test_delete_channel_success(self, mock_table):
        valid_uuid = '123e4567-e89b-12d3-a456-426614174000'

        mock_table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
          'name': 'Test Channel'
        }

        mock_table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()

        response = self.client.post(self.delete_url(valid_uuid))

        self.assertEqual(response.status_code, 302)

