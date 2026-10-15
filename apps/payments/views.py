import hmac

from django.conf import settings
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order

from .serializers import (
    InitializePaymentSerializer,
    InitializeServicePaymentSerializer,
    VerifyPaymentSerializer,
    VerifyServicePaymentSerializer,
)
from .services import (
    PaymentServiceError,
    fetch_verification,
    finalize_verification,
    initialize,
    verify,
)
from .service_payments import (
    fetch_service_verification,
    finalize_service_verification,
    initialize_service_payment,
    verify_service_transaction,
)


class InitializePaymentView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request):
        serializer = InitializePaymentSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        order = get_object_or_404(
            Order,
            id=(serializer.validated_data["order_id"]),
            user=request.user,
        )

        if order.payment_status == Order.PaymentStatus.PAID:
            return Response(
                {"detail": "Order already paid."},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            payment, data = initialize(
                order,
                serializer.validated_data["redirect_url"],
            )

        except PaymentServiceError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=(status.HTTP_502_BAD_GATEWAY),
            )

        provider_data = data.get("data") or {}

        return Response(
            {
                "payment_id": payment.id,
                "tx_ref": payment.tx_ref,
                "checkout_url": provider_data.get("link"),
                "payment_status": payment.status,
                "order_payment_status": (payment.order.payment_status),
            },
            status=status.HTTP_200_OK,
        )


class VerifyPaymentView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request):
        serializer = VerifyPaymentSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        transaction_id = serializer.validated_data["transaction_id"]

        try:
            # Fetching provider verification data
            # has no local state-changing side effect.
            payment, provider_response = fetch_verification(transaction_id)

        except PaymentServiceError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=(status.HTTP_502_BAD_GATEWAY),
            )

        # Authorization happens BEFORE inventory,
        # payment or order state can be modified.
        if payment.order.user_id != request.user.id:
            return Response(
                {"detail": "You do not have permission " "to verify this payment."},
                status=(status.HTTP_403_FORBIDDEN),
            )

        try:
            payment, verified = finalize_verification(
                payment=payment,
                transaction_id=transaction_id,
                provider_response=(provider_response),
            )

        except PaymentServiceError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=(status.HTTP_409_CONFLICT),
            )

        payment.refresh_from_db()
        payment.order.refresh_from_db()

        return Response(
            {
                "verified": verified,
                "payment_status": payment.status,
                "order_payment_status": (payment.order.payment_status),
            },
            status=status.HTTP_200_OK,
        )


class InitializeServicePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InitializeServicePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment, data = initialize_service_payment(
                user=request.user,
                service_type=serializer.validated_data["service_type"],
                service_id=serializer.validated_data["service_id"],
                redirect_url=serializer.validated_data["redirect_url"],
            )
        except PaymentServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        provider_data = data.get("data") or {}
        return Response({
            "payment_id": str(payment.id),
            "tx_ref": payment.tx_ref,
            "checkout_url": provider_data.get("link"),
            "payment_status": payment.status,
        }, status=status.HTTP_200_OK)


class VerifyServicePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VerifyServicePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transaction_id = serializer.validated_data["transaction_id"]
        try:
            payment, provider_response = fetch_service_verification(transaction_id)
        except PaymentServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        if payment.user_id != request.user.id:
            return Response({"detail": "You do not have permission to verify this service payment."}, status=status.HTTP_403_FORBIDDEN)
        try:
            payment, verified = finalize_service_verification(
                payment=payment,
                transaction_id=transaction_id,
                provider_response=provider_response,
            )
        except PaymentServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response({
            "verified": verified,
            "payment_status": payment.status,
            "service_type": payment.service_type,
        }, status=status.HTTP_200_OK)


class FlutterwaveWebhookView(APIView):
    authentication_classes = []
    permission_classes = [
        AllowAny,
    ]

    def post(self, request):
        signature = request.headers.get(
            "verif-hash",
            "",
        )

        secret_hash = settings.FLUTTERWAVE_SECRET_HASH or ""

        if (
            not secret_hash
            or not signature
            or not hmac.compare_digest(
                signature,
                secret_hash,
            )
        ):
            return Response(
                {"detail": "Invalid signature."},
                status=(status.HTTP_401_UNAUTHORIZED),
            )

        transaction_id = (request.data.get("data") or {}).get("id")

        if not transaction_id:
            return Response(
                {
                    "received": True,
                    "verification": "ignored",
                },
                status=status.HTTP_200_OK,
            )

        try:
            try:
                payment, verified = verify(str(transaction_id))
            except PaymentServiceError:
                payment, verified = verify_service_transaction(str(transaction_id))

        except (PaymentServiceError, ValidationError):
            # A valid Flutterwave webhook reached us,
            # but provider verification/finalization
            # could not currently complete.
            #
            # We intentionally do not expose internal
            # payment/provider information here.
            return Response(
                {
                    "received": True,
                    "verification": "deferred",
                },
                status=(status.HTTP_202_ACCEPTED),
            )

        return Response(
            {
                "received": True,
                "verified": verified,
                "payment_status": payment.status,
            },
            status=status.HTTP_200_OK,
        )


flutterwave_webhook = FlutterwaveWebhookView.as_view()
