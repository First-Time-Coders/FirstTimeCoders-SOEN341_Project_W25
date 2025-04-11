from unittest.mock import patch, MagicMock
from django.test import Client, TestCase
from django.urls import reverse
from django.contrib import messages

from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse


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

class AddMemberRequestTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.channel_id = '456e4567-e89b-12d3-a456-426614174999'
        session = self.client.session
        session['user_uuid'] = '123e4567-e89b-12d3-a456-426614174000'
        session['username'] = 'Saf'
        session['role'] = 'Admin'
        session.save()

    @patch('api.views.supabase_client')
    def test_admin_adds_member_request(self, mock_supabase_client):
        target_username = 'newmember'

        mock_users_table = MagicMock()
        mock_users_table.select.return_value.eq.return_value.execute.return_value.data = [
            {'id': 'user-456'}
        ]

        mock_requests_table = MagicMock()
        mock_requests_table.insert.return_value.execute.return_value.data = [{'status': 'admin_request'}]

        mock_channel_members = MagicMock()
        mock_channel_members.select.return_value.eq.return_value.execute.return_value.data = []

        mock_channels_created = MagicMock()
        mock_channels_created.select.return_value.eq.return_value.execute.return_value.data = []

        mock_all_channels = MagicMock()
        mock_all_channels.select.return_value.in_.return_value.execute.return_value.data = []

        mock_users_list = MagicMock()
        mock_users_list.select.return_value.neq.return_value.execute.return_value.data = []

        mock_supabase_client.table.side_effect = [
            mock_users_table,
            mock_requests_table,
            mock_channel_members,
            mock_channels_created,
            mock_all_channels,
            mock_users_list
        ]

        response = self.client.post(
            reverse('add-member', args=[self.channel_id]),
            {'username': target_username}
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard-admin'))


class ProfileViewTestCase(TestCase):
    def setUp(self):
                self.client = Client()
                session = self.client.session
                session['user_uuid'] = 'uuid123'
                session.save()

            @patch('api.views.supabase_client')
        def test_profile_view_success(self, mock_supabase):
                mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                    'first name': 'Safouane',
                    'last name': 'Maghni',
                    'email': 'safouane@example.com',
                    'username': 'Saf',
                    'gender': 'Male',
                    'role': 'Admin',
                    'age': 22
                }

                response = self.client.get(reverse('profile'))

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Safouane')
                self.assertContains(response, 'Maghni')
                self.assertContains(response, 'safouane@example.com')
                self.assertContains(response, 'Saf')
                self.assertContains(response, 'Male')
                self.assertContains(response, 'Admin')



class EditProfileTest(TestCase):
    def setUp(self):
                self.client = Client()
                session = self.client.session
                session['user_uuid'] = 'uuid123'
                session.save()

            @patch('api.views.supabase_client')
    def test_edit_all_fields_success(self, mock_supabase):
                # Mock Supabase update and auth update responses
                mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{'id': 'uuid123'}]
                mock_supabase.auth.update_user.return_value = {}

                fields_to_test = {
                    "first_name": "Safouane",
                    "last_name": "Maghni",
                    "email": "safouane@example.com",
                    "gender": "Male",
                    "role": "Admin",
                    "username": "Saf"
                }

                for field, value in fields_to_test.items():
                    response = self.client.post(reverse('edit-profile'), {
                        'field': field,
                        'value': value
                    })
                    self.assertEqual(response.status_code, 302)
                    self.assertRedirects(response, reverse('profile'))