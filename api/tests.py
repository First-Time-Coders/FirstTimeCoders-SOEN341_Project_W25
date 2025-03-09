from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status


class APIFunctionalityTests(APITestCase):
    def setUp(self):
        # Set up initial data such as creating a test user via Supabase API
        self.base_url = "http://localhost:8000/api/"  # Adjust if needed
        self.test_user = {"username": "testuser", "password": "testpassword"}
        self.channel_data = {"name": "testchannel"}

        # Create a user first
        response = self.client.post(f"{self.base_url}register/", self.test_user, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.token = response.data.get("token")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_create_channel(self):
        response = self.client.post(f"{self.base_url}create-channel/", self.channel_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_send_message(self):
        message_data = {"channel": "testchannel", "message": "Hello World!"}
        response = self.client.post(f"{self.base_url}send-message/", message_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_delete_message(self):
        # Assume message ID 1 exists for this test
        response = self.client.delete(f"{self.base_url}delete-message/1/")
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT])

    def test_delete_channel(self):
        response = self.client.delete(f"{self.base_url}delete-channel/testchannel/")
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT])

    def test_add_member(self):
        member_data = {"channel": "testchannel", "username": "newmember"}
        response = self.client.post(f"{self.base_url}add-member/", member_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

