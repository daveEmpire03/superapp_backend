from decimal import Decimal, InvalidOperation
import secrets

import requests

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.parcels.models import ParcelShipment
from apps.rides.models import Ride

from .models import ServicePayment
from .services import BASE_URL, REQUEST_TIMEOUT, PaymentServiceError, headers


def _service_and_owner(user, service_type, service_id, *, lock=False):
    if service_type == ServicePayment.ServiceType.RIDE:
        queryset = Ride.objects.select_for_update() if lock else Ride.objects
        service = get_object_or_404(queryset, pk=service_id, passenger=user)
        if service.payment_method != Ride.PaymentMethod.ONLINE:
            raise ValidationError({"payment_method": "This ride was requested with cash payment."})
        if service.status in {Ride.Status.CANCELLED, Ride.Status.NO_DRIVER}:
            raise ValidationError({"ride": "This ride cannot be paid for in its current state."})
        return service, "ride", service.quoted_fare, service.payment_status, Ride.PaymentStatus
    if service_type == ServicePayment.ServiceType.PARCEL:
        queryset = ParcelShipment.objects.select_for_update() if lock else ParcelShipment.objects
        service = get_object_or_404(queryset, pk=service_id, sender=user)
        if service.payment_method != ParcelShipment.PaymentMethod.ONLINE:
            raise ValidationError({"payment_method": "This parcel was requested with cash payment."})
        if service.status in {ParcelShipment.Status.CANCELLED, ParcelShipment.Status.DELIVERED}:
            raise ValidationError({"parcel": "This parcel cannot be paid for in its current state."})
        return service, "parcel", service.quoted_fare, service.payment_status, ParcelShipment.PaymentStatus
    raise ValidationError({"service_type": "Use RIDE or PARCEL."})


@transaction.atomic
def initialize_service_payment(*, user, service_type, service_id, redirect_url):
    service, target_field, amount, payment_status, status_choices = _service_and_owner(
        user, service_type, service_id, lock=True
    )
    if payment_status == status_choices.PAID:
        raise ValidationError({"payment": "This service has already been paid."})

    existing = (
        ServicePayment.objects.select_for_update()
        .filter(
            user=user,
            service_type=service_type,
            **{f"{target_field}_id": service.pk},
            status=ServicePayment.Status.INITIALIZED,
        )
        .order_by("-created_at")
        .first()
    )
    if existing:
        link = ((existing.raw_response or {}).get("data") or {}).get("link")
        if link and (existing.raw_response or {}).get("status") == "success":
            if payment_status != status_choices.PENDING:
                service.payment_status = status_choices.PENDING
                service.save(update_fields=["payment_status", "updated_at"])
            return existing, existing.raw_response

    payment = ServicePayment.objects.create(
        user=user,
        service_type=service_type,
        **{target_field: service},
        tx_ref="BKM-SVC-" + secrets.token_hex(12).upper(),
        amount=amount,
        currency="NGN",
    )
    payload = {
        "tx_ref": payment.tx_ref,
        "amount": str(payment.amount),
        "currency": payment.currency,
        "redirect_url": redirect_url,
        "customer": {
            "email": user.email,
            "name": user.get_full_name() or user.username,
            "phonenumber": user.phone or "",
        },
        "customizations": {
            "title": "Bokku Mart",
            "description": f"Payment for {service_type.lower()} {service.pk}",
        },
        "meta": {"service_type": service_type, "service_id": str(service.pk)},
    }
    try:
        response = requests.post(
            f"{BASE_URL}/payments", headers=headers(), json=payload, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        payment.status = ServicePayment.Status.FAILED
        payment.raw_response = {"error": "Provider initialization failed."}
        payment.save(update_fields=["status", "raw_response", "updated_at"])
        raise PaymentServiceError("Unable to initialize service payment.") from exc

    checkout_link = (data.get("data") or {}).get("link")
    if data.get("status") != "success" or not checkout_link:
        payment.status = ServicePayment.Status.FAILED
        payment.raw_response = data
        payment.save(update_fields=["status", "raw_response", "updated_at"])
        raise PaymentServiceError("Flutterwave did not return a valid service checkout link.")

    payment.raw_response = data
    payment.save(update_fields=["raw_response", "updated_at"])
    service.payment_status = status_choices.PENDING
    service.save(update_fields=["payment_status", "updated_at"])
    return payment, data


def fetch_service_verification(transaction_id):
    try:
        response = requests.get(
            f"{BASE_URL}/transactions/{transaction_id}/verify",
            headers=headers(),
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise PaymentServiceError("Unable to verify service payment.") from exc

    provider_data = data.get("data") or {}
    tx_ref = provider_data.get("tx_ref")
    if not tx_ref:
        raise PaymentServiceError("Provider verification response has no payment reference.")
    try:
        payment = ServicePayment.objects.select_related("ride", "parcel", "user").get(tx_ref=tx_ref)
    except ServicePayment.DoesNotExist as exc:
        raise PaymentServiceError("Service payment reference was not found.") from exc
    return payment, data


def _verified_service_payment(payment, data):
    provider_data = data.get("data") or {}
    try:
        paid_amount = Decimal(str(provider_data.get("amount")))
    except (InvalidOperation, TypeError, ValueError):
        return False
    return (
        data.get("status") == "success"
        and provider_data.get("status") == "successful"
        and provider_data.get("tx_ref") == payment.tx_ref
        and str(provider_data.get("currency") or "").upper() == payment.currency.upper()
        and paid_amount >= payment.amount
    )


@transaction.atomic
def finalize_service_verification(*, payment, transaction_id, provider_response):
    payment = ServicePayment.objects.select_for_update().get(pk=payment.pk)
    if payment.status == ServicePayment.Status.SUCCESS:
        return payment, True

    if not _verified_service_payment(payment, provider_response):
        payment.status = ServicePayment.Status.FAILED
        payment.provider_transaction_id = str(transaction_id)
        payment.raw_response = provider_response
        payment.save(update_fields=["status", "provider_transaction_id", "raw_response", "updated_at"])
        return payment, False

    service, target_field, amount, payment_status, status_choices = _service_and_owner(
        payment.user, payment.service_type,
        payment.ride_id if payment.service_type == ServicePayment.ServiceType.RIDE else payment.parcel_id,
        lock=True,
    )
    if service.payment_status == status_choices.PAID:
        payment.status = ServicePayment.Status.SUCCESS
    else:
        if service.status in {
            Ride.Status.CANCELLED if payment.service_type == ServicePayment.ServiceType.RIDE else ParcelShipment.Status.CANCELLED,
        }:
            raise PaymentServiceError("Service was cancelled before payment could be finalized.")
        service.payment_status = status_choices.PAID
        service.save(update_fields=["payment_status", "updated_at"])
        payment.status = ServicePayment.Status.SUCCESS

    payment.provider_transaction_id = str(transaction_id)
    payment.raw_response = provider_response
    payment.save(update_fields=["status", "provider_transaction_id", "raw_response", "updated_at"])
    return payment, True


def verify_service_transaction(transaction_id):
    payment, data = fetch_service_verification(transaction_id)
    return finalize_service_verification(
        payment=payment, transaction_id=transaction_id, provider_response=data
    )
