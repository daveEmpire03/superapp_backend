from django.test import TestCase
from django.urls import reverse
class HealthTest(TestCase):
    def test_health(self):
        response=self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.json()["success"])
