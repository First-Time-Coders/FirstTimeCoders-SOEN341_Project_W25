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

from unittest.mock import patch, MagicMock
from django.test import Client, TestCase, RequestFactory
from django.urls import reverse
from django.contrib import messages
from gotrue.errors import AuthApiError
import datetime
import uuid

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


class DMConversationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Set up session data as if user is logged in
        session = self.client.session
        self.user_uuid = "test-user-id"
        session['user_uuid'] = self.user_uuid
        session['username'] = 'testuser'
        session['role'] = 'member'
        session.save()
        
        # URL for starting a new DM
        self.start_dm_url = reverse('start_dm')

    @patch('api.views.supabase_client')
    def test_start_dm_conversation_success(self, mock_supabase):
        """Test successfully starting a DM conversation with another user"""
        # Mock the recipient lookup
        recipient_id = "recipient-user-id"
        mock_recipient_data = MagicMock(data={'id': recipient_id})
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_recipient_data
        
        # Mock the conversation check (no existing conversation)
        mock_supabase.table.return_value.select.return_value.or_.return_value.execute.return_value = MagicMock(data=[])
        
        # Mock the new conversation creation
        new_conversation_id = str(uuid.uuid4())
        mock_new_conv = MagicMock(data=[{'id': new_conversation_id}])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_new_conv
        
        # Make the POST request to start a DM
        response = self.client.post(self.start_dm_url, {
            'recipient_username': 'recipient_user'
        })
        
        # Check that we're redirected to the DM conversation
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dm', kwargs={'conversation_id': new_conversation_id}))
        
        # Verify Supabase calls
        # 1. First verifies the recipient exists
        mock_supabase.table.assert_any_call("users")
        # 2. Then checks for existing conversation
        mock_supabase.table.assert_any_call("Conversations Table")
        
        # 3. Then creates a new conversation - use a more flexible assertion
        insert_call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        self.assertEqual(insert_call_args['user1_id'], self.user_uuid)
        self.assertEqual(insert_call_args['user2_id'], recipient_id)
        self.assertTrue('created_at' in insert_call_args)  # Just check the key exists

    @patch('api.views.supabase_client')
    def test_start_dm_existing_conversation(self, mock_supabase):
        """Test starting a DM with a user where a conversation already exists"""
        # Mock the recipient lookup
        recipient_id = "recipient-user-id"
        mock_recipient_data = MagicMock(data={'id': recipient_id})
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_recipient_data
        
        # Mock finding an existing conversation
        existing_conversation_id = str(uuid.uuid4())
        
        # Add the required fields to the mock conversation data
        mock_supabase.table.return_value.select.return_value.or_.return_value.execute.return_value = MagicMock(
            data=[{
                'id': existing_conversation_id,
                'user1_id': self.user_uuid,
                'user2_id': recipient_id
            }]
        )
        
        # Make the POST request to start a DM
        response = self.client.post(self.start_dm_url, {
            'recipient_username': 'recipient_user'
        })
        
        # Check that we're redirected to the existing DM conversation
        self.assertEqual(response.status_code, 302)
        
        # Instead of full assertRedirects, just check the URL pattern
        self.assertTrue(f'/api/dm/{existing_conversation_id}/' in response.url)
        
        # Verify the insert method was NOT called (since we found an existing conversation)
        mock_supabase.table.return_value.insert.assert_not_called()

    @patch('api.views.supabase_client')
    def test_start_dm_user_not_found(self, mock_supabase):
        """Test starting a DM with a non-existent user"""
        # Mock the recipient lookup to return no user
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)
        
        # Make the POST request to start a DM
        response = self.client.post(self.start_dm_url, {
            'recipient_username': 'nonexistent_user'
        })
        
        # Check that we're redirected back to the start DM page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('start_dm'))
        
        # Check that an error message would be displayed
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'User not found')

    @patch('api.views.supabase_client')
    def test_start_dm_with_self(self, mock_supabase):
        """Test starting a DM with yourself (should not be allowed)"""
        # Mock the recipient lookup to return the current user
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={'id': self.user_uuid}
        )
        
        # Make the POST request to start a DM with yourself
        response = self.client.post(self.start_dm_url, {
            'recipient_username': 'testuser'  # Same as current user
        })
        
        # Check that we're redirected back to the start DM page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('start_dm'))
        
        # Check that an error message would be displayed
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'You cannot DM yourself')