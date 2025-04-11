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

    def test_logout_view(self):
        session = self.client.session
        session['user_uuid'] = 'uuid123'
        session.save()

        response = self.client.get(reverse('logout'))
        self.assertNotIn('user_uuid', self.client.session)
        self.assertRedirects(response, reverse('login'))


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