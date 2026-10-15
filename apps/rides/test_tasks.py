from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import TestCase

from apps.parcels.models import ParcelShipment, ParcelStatusHistory
from apps.rides.models import Ride, RideStatusHistory
from apps.rides.tasks import expire_unassigned_mobility_requests


User = get_user_model()


class ExpireMobilityRequestsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="mobility-expiry@example.com",
            password="StrongTestPassword123!",
            is_email_verified=True,
            role=User.Role.CUSTOMER,
        )

    def _ride(self, *, payment_method=Ride.PaymentMethod.CASH, payment_status=Ride.PaymentStatus.UNPAID):
        ride = Ride.objects.create(
            passenger=self.user,
            vehicle_type=Ride.VehicleType.CAR,
            pickup_address="Agodi, Ibadan",
            pickup_latitude=Decimal("7.4000000"),
            pickup_longitude=Decimal("3.9000000"),
            destination_address="Bodija, Ibadan",
            destination_latitude=Decimal("7.4300000"),
            destination_longitude=Decimal("3.9200000"),
            quoted_fare=Decimal("1250.00"),
            payment_method=payment_method,
            payment_status=payment_status,
        )
        Ride.objects.filter(pk=ride.pk).update(
            created_at=timezone.now() - timedelta(minutes=30)
        )
        return ride

    def _parcel(self, *, payment_method=ParcelShipment.PaymentMethod.CASH, payment_status=ParcelShipment.PaymentStatus.UNPAID):
        parcel = ParcelShipment.objects.create(
            sender=self.user,
            package_size=ParcelShipment.PackageSize.SMALL,
            package_description="Documents",
            recipient_name="Ada",
            recipient_phone="08000000000",
            pickup_address="Agodi, Ibadan",
            pickup_latitude=Decimal("7.4000000"),
            pickup_longitude=Decimal("3.9000000"),
            destination_address="Bodija, Ibadan",
            destination_latitude=Decimal("7.4300000"),
            destination_longitude=Decimal("3.9200000"),
            estimated_distance_km=Decimal("4.00"),
            quoted_fare=Decimal("900.00"),
            payment_method=payment_method,
            payment_status=payment_status,
            delivery_code_hash="not-used-in-expiry-test",
        )
        ParcelShipment.objects.filter(pk=parcel.pk).update(
            created_at=timezone.now() - timedelta(minutes=30)
        )
        return parcel

    def test_old_cash_ride_is_marked_no_driver_and_history_is_recorded(self):
        ride = self._ride()
        result = expire_unassigned_mobility_requests()
        ride.refresh_from_db()
        self.assertEqual(ride.status, Ride.Status.NO_DRIVER)
        self.assertEqual(ride.status_history.filter(status=Ride.Status.NO_DRIVER).count(), 1)
        self.assertEqual(result["rides_marked_no_driver"], 1)

    def test_old_unpaid_online_ride_is_cancelled_not_dispatched(self):
        ride = self._ride(
            payment_method=Ride.PaymentMethod.ONLINE,
            payment_status=Ride.PaymentStatus.UNPAID,
        )
        expire_unassigned_mobility_requests()
        ride.refresh_from_db()
        self.assertEqual(ride.status, Ride.Status.CANCELLED)
        self.assertIsNotNone(ride.cancelled_at)
        self.assertEqual(ride.status_history.filter(status=Ride.Status.CANCELLED).count(), 1)

    def test_old_paid_online_ride_is_not_closed_without_refund_support(self):
        ride = self._ride(
            payment_method=Ride.PaymentMethod.ONLINE,
            payment_status=Ride.PaymentStatus.PAID,
        )
        expire_unassigned_mobility_requests()
        ride.refresh_from_db()
        self.assertEqual(ride.status, Ride.Status.REQUESTED)
        self.assertEqual(ride.status_history.count(), 0)

    def test_old_cash_parcel_is_marked_no_driver(self):
        parcel = self._parcel()
        result = expire_unassigned_mobility_requests()
        parcel.refresh_from_db()
        self.assertEqual(parcel.status, ParcelShipment.Status.NO_DRIVER)
        self.assertEqual(parcel.status_history.filter(status=ParcelShipment.Status.NO_DRIVER).count(), 1)
        self.assertEqual(result["parcels_marked_no_driver"], 1)

    def test_pending_online_payment_is_not_expired_during_provider_verification(self):
        ride = self._ride(
            payment_method=Ride.PaymentMethod.ONLINE,
            payment_status=Ride.PaymentStatus.PENDING,
        )
        expire_unassigned_mobility_requests()
        ride.refresh_from_db()
        self.assertEqual(ride.status, Ride.Status.REQUESTED)
