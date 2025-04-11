from unittest.mock import patch, MagicMock
from django.test import Client, TestCase
from django.urls import reverse
from django.contrib import messages

from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from gotrue.errors import AuthApiError
import datetime

from api.views import messages_view


class LogoutTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_logout_view_saf1(self):
        session = self.client.session
        session['user_uuid'] = '123e4567-e89b-12d3-a456-426614174000'  # ✅ Fixed UUID
        session['username'] = 'Saf'
        session['role'] = 'Admin'
        session.save()

        response = self.client.get(reverse('logout'))

        self.assertNotIn('user_uuid', self.client.session)
        self.assertNotIn('username', self.client.session)
        self.assertNotIn('role', self.client.session)

        self.assertRedirects(response, reverse('login'))

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


class MessagesViewTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user_uuid = "test-user-id"
        self.channel_id = "test-channel-id"
        self.session_data = {
            'user_uuid': self.user_uuid,
            'username': 'testuser',
            'role': 'member'
        }

    @patch("api.views.supabase_client")
    def test_messages_view_get_authorized_user(self, mock_supabase_client):
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=[{'id': 1}]),  # member_check
            MagicMock(data={'created_by': 'another-user'}),  # created_by_check
            MagicMock(data=[{'channel_id': self.channel_id}]),  # user_channels_query
            MagicMock(data=[]),  # admin_channels_query
            MagicMock(data=[]),  # general_channels_query
            MagicMock(data=[{'id': self.channel_id, 'name': 'Test Channel', 'created_by': 'another-user'}]),  # channels_query
            MagicMock(data={'name': 'Test Channel'}),  # channel_query
            MagicMock(data=[{'id': 1, 'channel_id': self.channel_id, 'user_id': self.user_uuid, 'message': 'Hello there!', 'created_at': '2024-04-10T12:00:00'}]),  # messages
            MagicMock(data=[{'user_id': self.user_uuid}]),  # user_ids from channel_members
            MagicMock(data={'created_by': 'another-user'}),  # channel created_by
            MagicMock(data=[{'id': self.user_uuid, 'username': 'testuser'}]),  # user info
            MagicMock(data={'username': 'testuser'})  # sender username
        ]

        request = self.factory.get(f'/api/messages/{self.channel_id}/')
        request.session = self.session_data

        response = messages_view(request, self.channel_id)

        self.assertEqual(response.status_code, 200)

        self.assertIn(b'Test Channel', response.content)

        self.assertIn(b'Hello there!', response.content)

        self.assertIn(b'testuser', response.content)

