from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.rides.models import Ride, RideDriverProfile


User = get_user_model()


class DriverDispatchApiTests(APITestCase):
    def setUp(self):
        self.passenger = User.objects.create_user(
            email="dispatch-passenger@example.com",
            password="StrongTestPassword123!",
            is_email_verified=True,
            role=User.Role.CUSTOMER,
        )
        self.driver = User.objects.create_user(
            email="dispatch-driver@example.com",
            password="StrongTestPassword123!",
            is_email_verified=True,
            role=User.Role.RIDER,
        )
        self.other_driver = User.objects.create_user(
            email="other-dispatch-driver@example.com",
            password="StrongTestPassword123!",
            is_email_verified=True,
            role=User.Role.RIDER,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.driver)
        self.profile = RideDriverProfile.objects.create(
            user=self.driver,
            vehicle_type=Ride.VehicleType.CAR,
            vehicle_plate="ABC-123-XY",
            is_available=True,
            current_latitude=Decimal("7.4000000"),
            current_longitude=Decimal("3.9000000"),
            last_location_at=timezone.now(),
        )
        self.ride = Ride.objects.create(
            passenger=self.passenger,
            vehicle_type=Ride.VehicleType.CAR,
            status=Ride.Status.REQUESTED,
            pickup_address="Agodi, Ibadan",
            pickup_latitude=Decimal("7.4010000"),
            pickup_longitude=Decimal("3.9010000"),
            destination_address="Bodija, Ibadan",
            destination_latitude=Decimal("7.4300000"),
            destination_longitude=Decimal("3.9200000"),
            quoted_fare=Decimal("1200.00"),
            payment_method=Ride.PaymentMethod.CASH,
        )

    def test_driver_can_only_set_up_own_profile(self):
        response = self.client.post(
            "/api/v1/rides/driver/profile/",
            {
                "vehicle_type": "MOTORCYCLE",
                "vehicle_plate": "abc-456-xy",
                "vehicle_make": "Honda",
                "vehicle_color": "Black",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

        self.profile.delete()
        response = self.client.post(
            "/api/v1/rides/driver/profile/",
            {
                "vehicle_type": "MOTORCYCLE",
                "vehicle_plate": "abc-456-xy",
                "vehicle_make": "Honda",
                "vehicle_color": "Black",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["vehicle_plate"], "ABC-456-XY")
        self.assertEqual(RideDriverProfile.objects.filter(user=self.driver).count(), 1)

    def test_driver_must_have_fresh_location_before_going_available(self):
        self.profile.last_location_at = timezone.now() - timezone.timedelta(minutes=6)
        self.profile.save(update_fields=["last_location_at"])
        response = self.client.post(
            "/api/v1/rides/driver/availability/",
            {"is_available": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.is_available)

    def test_available_ride_list_returns_only_nearby_matching_vehicle(self):
        far_ride = Ride.objects.create(
            passenger=self.passenger,
            vehicle_type=Ride.VehicleType.CAR,
            pickup_address="Far away",
            pickup_latitude=Decimal("7.8000000"),
            pickup_longitude=Decimal("3.9000000"),
            destination_address="Destination",
            destination_latitude=Decimal("7.8200000"),
            destination_longitude=Decimal("3.9200000"),
            quoted_fare=Decimal("1500.00"),
            payment_method=Ride.PaymentMethod.CASH,
        )
        motorcycle_ride = Ride.objects.create(
            passenger=self.passenger,
            vehicle_type=Ride.VehicleType.MOTORCYCLE,
            pickup_address="Nearby",
            pickup_latitude=Decimal("7.4010000"),
            pickup_longitude=Decimal("3.9010000"),
            destination_address="Destination",
            destination_latitude=Decimal("7.4300000"),
            destination_longitude=Decimal("3.9200000"),
            quoted_fare=Decimal("700.00"),
            payment_method=Ride.PaymentMethod.CASH,
        )

        response = self.client.get("/api/v1/rides/driver/available/")
        self.assertEqual(response.status_code, 200)
        ids = {item["ride"]["id"] for item in response.data["data"]}
        self.assertIn(str(self.ride.pk), ids)
        self.assertNotIn(str(far_ride.pk), ids)
        self.assertNotIn(str(motorcycle_ride.pk), ids)

    def test_accepting_ride_assigns_driver_and_records_history_atomically(self):
        response = self.client.post("/api/v1/rides/%s/accept/" % self.ride.pk, {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.ride.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.ride.driver, self.driver)
        self.assertEqual(self.ride.status, Ride.Status.DRIVER_ASSIGNED)
        self.assertIsNotNone(self.ride.driver_assigned_at)
        self.assertFalse(self.profile.is_available)
        self.assertEqual(
            self.ride.status_history.filter(status=Ride.Status.DRIVER_ASSIGNED).count(), 1
        )

    def test_unavailable_driver_cannot_accept_ride(self):
        self.profile.is_available = False
        self.profile.save(update_fields=["is_available"])
        response = self.client.post("/api/v1/rides/%s/accept/" % self.ride.pk, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.ride.refresh_from_db()
        self.assertIsNone(self.ride.driver)

    def test_driver_cannot_skip_lifecycle_transitions_or_update_another_drivers_ride(self):
        self.ride.driver = self.driver
        self.ride.status = Ride.Status.DRIVER_ASSIGNED
        self.ride.save(update_fields=["driver", "status"])
        response = self.client.post(
            "/api/v1/rides/%s/status/" % self.ride.pk,
            {"status": "COMPLETED"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.ride.refresh_from_db()
        self.assertEqual(self.ride.status, Ride.Status.DRIVER_ASSIGNED)

        self.ride.driver = self.other_driver
        self.ride.save(update_fields=["driver"])
        response = self.client.post(
            "/api/v1/rides/%s/status/" % self.ride.pk,
            {"status": "DRIVER_ARRIVING"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_valid_driver_lifecycle_records_timestamps_and_history(self):
        self.ride.driver = self.driver
        self.ride.status = Ride.Status.DRIVER_ASSIGNED
        self.ride.save(update_fields=["driver", "status"])

        arriving = self.client.post(
            "/api/v1/rides/%s/status/" % self.ride.pk,
            {"status": "DRIVER_ARRIVING"},
            format="json",
        )
        self.assertEqual(arriving.status_code, 200)
        started = self.client.post(
            "/api/v1/rides/%s/status/" % self.ride.pk,
            {"status": "IN_PROGRESS"},
            format="json",
        )
        self.assertEqual(started.status_code, 200)
        completed = self.client.post(
            "/api/v1/rides/%s/status/" % self.ride.pk,
            {"status": "COMPLETED"},
            format="json",
        )
        self.assertEqual(completed.status_code, 200)

        self.ride.refresh_from_db()
        self.assertEqual(self.ride.status, Ride.Status.COMPLETED)
        self.assertIsNotNone(self.ride.trip_started_at)
        self.assertIsNotNone(self.ride.trip_completed_at)
        self.assertEqual(
            list(self.ride.status_history.values_list("status", flat=True)),
            [
                Ride.Status.DRIVER_ARRIVING,
                Ride.Status.IN_PROGRESS,
                Ride.Status.COMPLETED,
            ],
        )

    def test_customer_cannot_use_driver_availability_endpoint(self):
        self.client.force_authenticate(self.passenger)
        response = self.client.post(
            "/api/v1/rides/driver/availability/",
            {"is_available": True},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
