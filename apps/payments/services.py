import secrets
from decimal import (
    Decimal,
    InvalidOperation,
)

import requests

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from rest_framework.exceptions import ValidationError

from apps.orders.inventory_service import (
    commit_reserved_inventory,
)
from apps.orders.models import (
    Order,
    OrderStatusHistory,
)

from .models import Payment


BASE_URL = "https://api.flutterwave.com/v3"
REQUEST_TIMEOUT = 20


class PaymentServiceError(Exception):
    """Raised when a payment provider operation fails."""


def headers():
    if not settings.FLUTTERWAVE_SECRET_KEY:
        raise PaymentServiceError("Flutterwave secret key is not configured.")

    return {
        "Authorization": (f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}"),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def generate_tx_ref():
    return "BKM-PAY-" + secrets.token_hex(12).upper()


def _to_decimal(value):
    try:
        return Decimal(str(value))

    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ):
        return Decimal("0.00")


@transaction.atomic
def initialize(
    order,
    redirect_url,
):
    """
    Initialize Flutterwave checkout.

    The order is locked so two concurrent requests
    cannot independently create payment attempts.

    An existing INITIALIZED payment for the same
    still-valid order may be reused when it already
    contains a valid Flutterwave checkout link.
    """

    order = Order.objects.select_for_update().select_related("user").get(id=order.id)

    if order.payment_status == Order.PaymentStatus.PAID:
        raise ValidationError({"order": "This order has already been paid."})

    if order.status in {
        Order.Status.CANCELLED,
        Order.Status.EXPIRED,
    }:
        raise ValidationError(
            {"order": ("Payment cannot be initialized " "for this order.")}
        )

    if order.reservation_expires_at and order.reservation_expires_at <= timezone.now():
        raise ValidationError({"order": "The checkout reservation has expired."})

    existing_payment = (
        Payment.objects.select_for_update()
        .filter(
            order=order,
            status=Payment.Status.INITIALIZED,
        )
        .order_by("-created_at")
        .first()
    )

    if existing_payment:
        existing_data = existing_payment.raw_response or {}

        existing_link = (existing_data.get("data") or {}).get("link")

        if existing_data.get("status") == "success" and existing_link:
            if order.payment_status != Order.PaymentStatus.PENDING:
                order.payment_status = Order.PaymentStatus.PENDING

                order.save(
                    update_fields=[
                        "payment_status",
                        "updated_at",
                    ]
                )

            return (
                existing_payment,
                existing_data,
            )

    payment = Payment.objects.create(
        order=order,
        tx_ref=generate_tx_ref(),
        amount=order.total,
        currency="NGN",
        status=Payment.Status.INITIALIZED,
    )

    payload = {
        "tx_ref": payment.tx_ref,
        "amount": str(payment.amount),
        "currency": payment.currency,
        "redirect_url": redirect_url,
        "customer": {
            "email": order.user.email,
            "name": (order.user.get_full_name() or order.user.username),
            "phonenumber": (order.user.phone or ""),
        },
        "customizations": {
            "title": "Bokku Mart",
            "description": (f"Payment for {order.reference}"),
        },
        "configurations": {
            "session_duration": 15,
            "max_retry_attempt": 5,
        },
        "meta": {
            "order_id": str(order.id),
            "order_reference": order.reference,
        },
    }

    try:
        response = requests.post(
            f"{BASE_URL}/payments",
            headers=headers(),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()
        data = response.json()

    except (
        requests.RequestException,
        ValueError,
    ) as exc:
        payment.status = Payment.Status.FAILED

        payment.raw_response = {
            "error": str(exc),
        }

        payment.save(
            update_fields=[
                "status",
                "raw_response",
                "updated_at",
            ]
        )

        raise PaymentServiceError("Unable to initialize payment.") from exc

    checkout_link = (data.get("data") or {}).get("link")

    if data.get("status") != "success" or not checkout_link:
        payment.status = Payment.Status.FAILED
        payment.raw_response = data

        payment.save(
            update_fields=[
                "status",
                "raw_response",
                "updated_at",
            ]
        )

        raise PaymentServiceError(
            "Flutterwave did not return " "a valid checkout link."
        )

    payment.raw_response = data

    payment.save(
        update_fields=[
            "raw_response",
            "updated_at",
        ]
    )

    order.payment_status = Order.PaymentStatus.PENDING

    order.save(
        update_fields=[
            "payment_status",
            "updated_at",
        ]
    )

    return payment, data


def fetch_verification(transaction_id):
    """
    Retrieve and validate enough Flutterwave data
    to identify our local Payment.

    This function DOES NOT modify Payment, Order
    or inventory state.
    """

    try:
        response = requests.get(
            (f"{BASE_URL}/transactions/" f"{transaction_id}/verify"),
            headers=headers(),
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()
        data = response.json()

    except (
        requests.RequestException,
        ValueError,
    ) as exc:
        raise PaymentServiceError("Unable to verify payment.") from exc

    provider_data = data.get("data") or {}

    tx_ref = provider_data.get("tx_ref")

    if not tx_ref:
        raise PaymentServiceError(
            "Flutterwave verification response " "does not contain tx_ref."
        )

    try:
        payment = Payment.objects.select_related("order").get(tx_ref=tx_ref)

    except Payment.DoesNotExist as exc:
        raise PaymentServiceError("Payment reference was not found.") from exc

    return payment, data


def _provider_payment_is_valid(
    *,
    payment,
    provider_response,
):
    provider_data = provider_response.get("data") or {}

    provider_status = provider_data.get("status")

    provider_currency = str(provider_data.get("currency") or "").upper()

    provider_amount = _to_decimal(provider_data.get("amount"))

    expected_amount = Decimal(payment.amount)

    expected_currency = payment.currency.upper()

    return (
        provider_response.get("status") == "success"
        and provider_status == "successful"
        and provider_data.get("tx_ref") == payment.tx_ref
        and provider_currency == expected_currency
        and provider_amount >= expected_amount
    )


@transaction.atomic
def _finalize_successful_payment(
    *,
    payment_id,
    transaction_id,
    provider_response,
):
    """
    Idempotently finalize a verified payment.

    Payment, Order, inventory and audit movements
    are committed in the same transaction.
    """

    payment = (
        Payment.objects.select_for_update()
        .select_related(
            "order",
            "order__store",
        )
        .get(id=payment_id)
    )

    order = Order.objects.select_for_update().get(id=payment.order_id)

    if (
        payment.status == Payment.Status.SUCCESS
        and order.payment_status == Order.PaymentStatus.PAID
        and order.inventory_committed
    ):
        payment.provider_transaction_id = str(transaction_id)

        payment.raw_response = provider_response

        payment.save(
            update_fields=[
                "provider_transaction_id",
                "raw_response",
                "updated_at",
            ]
        )

        return payment

    if order.status in {
        Order.Status.CANCELLED,
        Order.Status.EXPIRED,
    }:
        raise PaymentServiceError(
            "Payment was verified for an order " "that can no longer be fulfilled."
        )

    if order.reservation_expires_at and order.reservation_expires_at <= timezone.now():
        raise PaymentServiceError(
            "Payment was verified after the " "inventory reservation expired."
        )

    commit_reserved_inventory(
        order,
        performed_by=None,
    )

    payment.status = Payment.Status.SUCCESS

    payment.provider_transaction_id = str(transaction_id)

    payment.raw_response = provider_response

    order.payment_status = Order.PaymentStatus.PAID

    if order.status == Order.Status.PENDING:
        order.status = Order.Status.CONFIRMED

    order.reservation_expires_at = None

    payment.save(
        update_fields=[
            "status",
            "provider_transaction_id",
            "raw_response",
            "updated_at",
        ]
    )

    order.save(
        update_fields=[
            "payment_status",
            "status",
            "inventory_committed",
            "reservation_expires_at",
            "updated_at",
        ]
    )

    status_history_exists = OrderStatusHistory.objects.filter(
        order=order,
        status=Order.Status.CONFIRMED,
    ).exists()

    if not status_history_exists:
        OrderStatusHistory.objects.create(
            order=order,
            status=Order.Status.CONFIRMED,
            note="Payment verified successfully.",
        )

    return payment


def _mark_payment_failed(
    *,
    payment_id,
    transaction_id,
    provider_response,
):
    """
    Record failed verification.

    The stock reservation remains until checkout
    expiration so the customer may retry.
    """

    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(id=payment_id)

        if payment.status == Payment.Status.SUCCESS:
            return payment

        payment.status = Payment.Status.FAILED

        payment.provider_transaction_id = str(transaction_id)

        payment.raw_response = provider_response

        payment.save(
            update_fields=[
                "status",
                "provider_transaction_id",
                "raw_response",
                "updated_at",
            ]
        )

        return payment


def finalize_verification(
    *,
    payment,
    transaction_id,
    provider_response,
):
    """
    Finalize verification after the caller has
    performed any required authorization.
    """

    if not _provider_payment_is_valid(
        payment=payment,
        provider_response=provider_response,
    ):
        payment = _mark_payment_failed(
            payment_id=payment.id,
            transaction_id=transaction_id,
            provider_response=provider_response,
        )

        return payment, False

    payment = _finalize_successful_payment(
        payment_id=payment.id,
        transaction_id=transaction_id,
        provider_response=provider_response,
    )

    return payment, True


def verify(transaction_id):
    """
    Trusted server-side verification path.

    Intended for Flutterwave webhook processing.
    """

    payment, data = fetch_verification(transaction_id)

    return finalize_verification(
        payment=payment,
        transaction_id=transaction_id,
        provider_response=data,
    )
