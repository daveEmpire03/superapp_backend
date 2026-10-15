from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.parcels.models import ParcelShipment
from apps.rides.models import RideDriverProfile


User = get_user_model()


class ParcelApiTests(TestCase):
    def setUp(self):
        self.sender = User.objects.create_user(
            email="parcel-sender@example.com", password="StrongTestPassword123!",
            is_email_verified=True, role=User.Role.CUSTOMER,
        )
        self.driver = User.objects.create_user(
            email="parcel-driver@example.com", password="StrongTestPassword123!",
            is_email_verified=True, role=User.Role.RIDER,
        )
        self.profile = RideDriverProfile.objects.create(
            user=self.driver, vehicle_type="CAR", vehicle_plate="ABC-123-XY",
            is_available=True, is_approved=True, current_latitude=Decimal("7.4000000"),
            current_longitude=Decimal("3.9000000"), last_location_at=timezone.now(),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.sender)
        self.payload = {
            "package_size": "SMALL", "package_description": "Documents",
            "recipient_name": "Ada", "recipient_phone": "08000000000",
            "pickup_address": "Agodi, Ibadan", "pickup_latitude": "7.4000", "pickup_longitude": "3.9000",
            "destination_address": "Bodija, Ibadan", "destination_latitude": "7.4300", "destination_longitude": "3.9200",
            "payment_method": "CASH",
        }

    def test_quote_does_not_create_parcel(self):
        response = self.client.post("/api/v1/parcels/quote/", {k: v for k, v in self.payload.items() if k != "payment_method"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["is_estimate"])
        self.assertGreater(Decimal(response.data["data"]["quoted_fare"]), Decimal("0"))
        self.assertEqual(ParcelShipment.objects.count(), 0)

    def test_create_returns_one_time_delivery_code_and_ignores_client_state(self):
        response = self.client.post("/api/v1/parcels/", {**self.payload, "status": "DELIVERED", "quoted_fare": "0.01"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("delivery_code", response.data["data"])
        parcel = ParcelShipment.objects.get()
        self.assertEqual(parcel.sender, self.sender)
        self.assertEqual(parcel.status, ParcelShipment.Status.REQUESTED)
        self.assertGreater(parcel.quoted_fare, Decimal("0.01"))
        self.assertNotIn("delivery_code_hash", response.data["data"])

    def test_sender_cannot_read_other_senders_parcel(self):
        created = self.client.post("/api/v1/parcels/", self.payload, format="json")
        parcel_id = created.data["data"]["id"]
        other = User.objects.create_user(email="other-sender@example.com", password="StrongTestPassword123!", role=User.Role.CUSTOMER)
        self.client.force_authenticate(other)
        detail = self.client.get(f"/api/v1/parcels/{parcel_id}/")
        self.assertEqual(detail.status_code, 404)

    def test_driver_must_be_approved_available_and_nearby_to_accept(self):
        self.client.force_authenticate(self.sender)
        created = self.client.post("/api/v1/parcels/", self.payload, format="json")
        parcel_id = created.data["data"]["id"]
        self.client.force_authenticate(self.driver)
        response = self.client.post(f"/api/v1/parcels/{parcel_id}/accept/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        parcel = ParcelShipment.objects.get()
        self.profile.refresh_from_db()
        self.assertEqual(parcel.driver, self.driver)
        self.assertEqual(parcel.status, ParcelShipment.Status.DRIVER_ASSIGNED)
        self.assertFalse(self.profile.is_available)

    def test_delivery_requires_valid_confirmation_code(self):
        self.client.force_authenticate(self.sender)
        created = self.client.post("/api/v1/parcels/", self.payload, format="json")
        parcel = ParcelShipment.objects.get()
        code = created.data["data"]["delivery_code"]
        parcel.driver = self.driver
        parcel.status = ParcelShipment.Status.IN_TRANSIT
        from django.contrib.auth.hashers import make_password
        parcel.delivery_code_hash = make_password(code)
        parcel.save(update_fields=["driver", "status", "delivery_code_hash"])
        self.client.force_authenticate(self.driver)
        bad = self.client.patch(f"/api/v1/parcels/{parcel.pk}/status/", {"status": "DELIVERED", "delivery_code": "000000"}, format="json")
        self.assertEqual(bad.status_code, 400)
        good = self.client.patch(f"/api/v1/parcels/{parcel.pk}/status/", {"status": "DELIVERED", "delivery_code": code}, format="json")
        self.assertEqual(good.status_code, 200)
        parcel.refresh_from_db()
        self.assertEqual(parcel.status, ParcelShipment.Status.DELIVERED)
        self.assertNotIn(code, parcel.delivery_code_hash)
