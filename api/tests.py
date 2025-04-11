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
