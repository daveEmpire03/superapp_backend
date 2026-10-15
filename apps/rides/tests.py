from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.rides.models import Ride, RideStatusHistory


User = get_user_model()


class RideModelTests(TestCase):
    def setUp(self):
        self.passenger = User.objects.create_user(
            email="passenger@example.com",
            password="test-password",
        )
        self.driver = User.objects.create_user(
            email="driver@example.com",
            password="test-password",
            role=User.Role.RIDER,
        )

    def ride_data(self):
        return {
            "passenger": self.passenger,
            "vehicle_type": Ride.VehicleType.CAR,
            "pickup_address": "Pickup, Ibadan",
            "pickup_latitude": Decimal("7.3775"),
            "pickup_longitude": Decimal("3.9470"),
            "destination_address": "Destination, Ibadan",
            "destination_latitude": Decimal("7.4000"),
            "destination_longitude": Decimal("3.9600"),
            "quoted_fare": Decimal("2500.00"),
            "payment_method": Ride.PaymentMethod.CASH,
        }

    def test_ride_is_independent_of_grocery_order_and_defaults(self):
        ride = Ride.objects.create(**self.ride_data())

        self.assertEqual(ride.status, Ride.Status.REQUESTED)
        self.assertEqual(ride.payment_status, Ride.PaymentStatus.UNPAID)
        self.assertEqual(ride.currency, "NGN")
        self.assertFalse(hasattr(ride, "order"))

    def test_driver_can_be_assigned_and_history_recorded(self):
        ride = Ride.objects.create(**self.ride_data(), driver=self.driver)
        history = RideStatusHistory.objects.create(
            ride=ride,
            status=Ride.Status.DRIVER_ASSIGNED,
            changed_by=self.driver,
        )

        self.assertEqual(ride.driver.role, User.Role.RIDER)
        self.assertEqual(history.ride_id, ride.pk)

    def test_negative_quoted_fare_is_rejected_by_database(self):
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Ride.objects.create(**{**self.ride_data(), "quoted_fare": Decimal("-1.00")})
