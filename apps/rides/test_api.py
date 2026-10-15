from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.rides.models import Ride, RideStatusHistory


User = get_user_model()


class PassengerRideApiTests(TestCase):
    def setUp(self):
        self.passenger = User.objects.create_user(
            email="ride-passenger@example.com",
            password="StrongTestPassword123!",
            is_email_verified=True,
            role=User.Role.CUSTOMER,
        )
        self.other_passenger = User.objects.create_user(
            email="other-passenger@example.com",
            password="StrongTestPassword123!",
            is_email_verified=True,
            role=User.Role.CUSTOMER,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.passenger)
        self.payload = {
            "vehicle_type": "CAR",
            "pickup_address": "Agodi, Ibadan",
            "pickup_latitude": "7.4000",
            "pickup_longitude": "3.9000",
            "destination_address": "Bodija, Ibadan",
            "destination_latitude": "7.4300",
            "destination_longitude": "3.9200",
            "payment_method": "CASH",
            "passenger_note": "I will be at the gate.",
        }

    def test_quote_is_server_calculated_and_does_not_create_a_ride(self):
        response = self.client.post(
            "/api/v1/rides/quote/",
            {key: value for key, value in self.payload.items() if key not in {
                "payment_method", "passenger_note"
            }},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["currency"], "NGN")
        self.assertTrue(response.data["data"]["is_estimate"])
        self.assertGreater(Decimal(response.data["data"]["quoted_fare"]), Decimal("0"))
        self.assertEqual(Ride.objects.count(), 0)

    def test_request_ignores_client_supplied_fare_and_payment_status(self):
        response = self.client.post(
            "/api/v1/rides/",
            {
                **self.payload,
                "quoted_fare": "0.01",
                "payment_status": "PAID",
                "status": "COMPLETED",
                "passenger": str(self.other_passenger.pk),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        ride = Ride.objects.get()
        self.assertEqual(ride.passenger, self.passenger)
        self.assertEqual(ride.status, Ride.Status.REQUESTED)
        self.assertEqual(ride.payment_status, Ride.PaymentStatus.UNPAID)
        self.assertGreater(ride.quoted_fare, Decimal("0.01"))
        self.assertEqual(ride.status_history.count(), 1)
        self.assertEqual(ride.status_history.first().status, Ride.Status.REQUESTED)

    def test_passenger_can_only_list_and_retrieve_own_rides(self):
        own_ride = self.client.post("/api/v1/rides/", self.payload, format="json")
        self.assertEqual(own_ride.status_code, 201)
        other_ride = Ride.objects.create(
            passenger=self.other_passenger,
            vehicle_type=Ride.VehicleType.CAR,
            pickup_address="A",
            pickup_latitude=Decimal("7.4000"),
            pickup_longitude=Decimal("3.9000"),
            destination_address="B",
            destination_latitude=Decimal("7.4300"),
            destination_longitude=Decimal("3.9200"),
            quoted_fare=Decimal("500.00"),
            payment_method=Ride.PaymentMethod.CASH,
        )

        listing = self.client.get("/api/v1/rides/")
        self.assertEqual(listing.status_code, 200)
        results = listing.data.get("results", listing.data)
        returned_ids = {str(item["id"]) for item in results}
        self.assertIn(str(own_ride.data["data"]["id"]), returned_ids)
        self.assertNotIn(str(other_ride.pk), returned_ids)

        detail = self.client.get(f"/api/v1/rides/{other_ride.pk}/")
        self.assertEqual(detail.status_code, 404)

    def test_rejects_identical_pickup_and_destination(self):
        payload = {
            **self.payload,
            "destination_latitude": self.payload["pickup_latitude"],
            "destination_longitude": self.payload["pickup_longitude"],
        }
        response = self.client.post("/api/v1/rides/", payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Ride.objects.count(), 0)

    def test_rider_account_cannot_request_passenger_trip(self):
        rider = User.objects.create_user(
            email="ride-driver@example.com",
            password="StrongTestPassword123!",
            is_email_verified=True,
            role=User.Role.RIDER,
        )
        self.client.force_authenticate(rider)
        response = self.client.post("/api/v1/rides/", self.payload, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Ride.objects.count(), 0)

    def test_unauthenticated_user_cannot_request_ride(self):
        self.client.force_authenticate(user=None)
        response = self.client.post("/api/v1/rides/", self.payload, format="json")
        self.assertEqual(response.status_code, 401)

    def test_passenger_cannot_cancel_ride_with_pending_online_payment(self):
        response = self.client.post(
            "/api/v1/rides/",
            {**self.payload, "payment_method": "ONLINE"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        ride = Ride.objects.get()
        ride.payment_status = Ride.PaymentStatus.PENDING
        ride.save(update_fields=["payment_status"])
        cancelled = self.client.post(
            "/api/v1/rides/%s/cancel/" % ride.pk,
            {"reason": "Changed plans"},
            format="json",
        )
        self.assertEqual(cancelled.status_code, 400)
        ride.refresh_from_db()
        self.assertEqual(ride.status, Ride.Status.REQUESTED)
