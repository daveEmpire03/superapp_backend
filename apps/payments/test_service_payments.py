from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.parcels.models import ParcelShipment
from apps.payments.models import ServicePayment
from apps.rides.models import Ride


User = get_user_model()


@override_settings(FLUTTERWAVE_SECRET_KEY="test-flutterwave-secret")
class ServicePaymentApiTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="mobility-payment-owner@example.com",
            password="StrongTestPassword123!",
            is_email_verified=True,
            role=User.Role.CUSTOMER,
        )
        self.other_user = User.objects.create_user(
            email="mobility-payment-other@example.com",
            password="StrongTestPassword123!",
            is_email_verified=True,
            role=User.Role.CUSTOMER,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.ride = Ride.objects.create(
            passenger=self.owner,
            vehicle_type=Ride.VehicleType.CAR,
            pickup_address="Agodi, Ibadan",
            pickup_latitude=Decimal("7.4000000"),
            pickup_longitude=Decimal("3.9000000"),
            destination_address="Bodija, Ibadan",
            destination_latitude=Decimal("7.4300000"),
            destination_longitude=Decimal("3.9200000"),
            quoted_fare=Decimal("1250.00"),
            payment_method=Ride.PaymentMethod.ONLINE,
        )

    def test_initialize_service_payment_uses_server_amount_and_marks_pending(self):
        provider_response = Mock()
        provider_response.json.return_value = {
            "status": "success",
            "data": {"link": "https://checkout.flutterwave.com/test"},
        }
        provider_response.raise_for_status.return_value = None

        with patch("apps.payments.service_payments.requests.post", return_value=provider_response) as post:
            response = self.client.post(
                "/api/v1/payments/services/initialize/",
                {
                    "service_type": "RIDE",
                    "service_id": str(self.ride.pk),
                    "redirect_url": "https://bokkumart.ng/payment/return",
                },
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["checkout_url"], "https://checkout.flutterwave.com/test")
        payment = ServicePayment.objects.get()
        self.assertEqual(payment.amount, Decimal("1250.00"))
        self.assertEqual(payment.user, self.owner)
        self.assertEqual(payment.ride, self.ride)
        self.ride.refresh_from_db()
        self.assertEqual(self.ride.payment_status, Ride.PaymentStatus.PENDING)
        self.assertEqual(post.call_args.kwargs["json"]["amount"], "1250.00")

    def test_other_user_cannot_finalize_service_payment(self):
        payment = ServicePayment.objects.create(
            user=self.owner,
            service_type=ServicePayment.ServiceType.RIDE,
            ride=self.ride,
            tx_ref="BKM-SVC-OWNER-ONLY",
            amount=Decimal("1250.00"),
            currency="NGN",
        )
        provider_response = Mock()
        provider_response.json.return_value = {
            "status": "success",
            "data": {
                "tx_ref": payment.tx_ref,
                "status": "successful",
                "currency": "NGN",
                "amount": 1250,
            },
        }
        provider_response.raise_for_status.return_value = None
        self.client.force_authenticate(self.other_user)

        with patch("apps.payments.service_payments.requests.get", return_value=provider_response):
            response = self.client.post(
                "/api/v1/payments/services/verify/",
                {"transaction_id": "123456"},
                format="json",
            )

        self.assertEqual(response.status_code, 403)
        payment.refresh_from_db()
        self.ride.refresh_from_db()
        self.assertEqual(payment.status, ServicePayment.Status.INITIALIZED)
        self.assertEqual(self.ride.payment_status, Ride.PaymentStatus.UNPAID)

    def test_successful_provider_verification_marks_ride_paid_idempotently(self):
        payment = ServicePayment.objects.create(
            user=self.owner,
            service_type=ServicePayment.ServiceType.RIDE,
            ride=self.ride,
            tx_ref="BKM-SVC-VERIFY-OK",
            amount=Decimal("1250.00"),
            currency="NGN",
        )
        provider_response = Mock()
        provider_response.json.return_value = {
            "status": "success",
            "data": {
                "tx_ref": payment.tx_ref,
                "status": "successful",
                "currency": "NGN",
                "amount": 1250,
            },
        }
        provider_response.raise_for_status.return_value = None

        with patch("apps.payments.service_payments.requests.get", return_value=provider_response):
            response = self.client.post(
                "/api/v1/payments/services/verify/",
                {"transaction_id": "123456"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["verified"])
        payment.refresh_from_db()
        self.ride.refresh_from_db()
        self.assertEqual(payment.status, ServicePayment.Status.SUCCESS)
        self.assertEqual(self.ride.payment_status, Ride.PaymentStatus.PAID)

        with patch("apps.payments.service_payments.requests.get", return_value=provider_response):
            repeated = self.client.post(
                "/api/v1/payments/services/verify/",
                {"transaction_id": "123456"},
                format="json",
            )
        self.assertEqual(repeated.status_code, 200)
        self.assertTrue(repeated.data["verified"])
        self.assertEqual(ServicePayment.objects.count(), 1)

    def test_initialize_service_payment_supports_parcels_without_order_payment_coupling(self):
        parcel = ParcelShipment.objects.create(
            sender=self.owner,
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
            payment_method=ParcelShipment.PaymentMethod.ONLINE,
            delivery_code_hash="not-used-in-this-payment-test",
        )
        provider_response = Mock()
        provider_response.json.return_value = {
            "status": "success",
            "data": {"link": "https://checkout.flutterwave.com/parcel-test"},
        }
        provider_response.raise_for_status.return_value = None

        with patch("apps.payments.service_payments.requests.post", return_value=provider_response):
            response = self.client.post(
                "/api/v1/payments/services/initialize/",
                {
                    "service_type": "PARCEL",
                    "service_id": str(parcel.pk),
                    "redirect_url": "https://bokkumart.ng/payment/return",
                },
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        payment = ServicePayment.objects.get(service_type=ServicePayment.ServiceType.PARCEL)
        self.assertEqual(payment.parcel, parcel)
        self.assertIsNone(payment.ride_id)
        parcel.refresh_from_db()
        self.assertEqual(parcel.payment_status, ParcelShipment.PaymentStatus.PENDING)
