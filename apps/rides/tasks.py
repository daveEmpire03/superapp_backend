import os
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from apps.parcels.models import ParcelShipment, ParcelStatusHistory
from apps.rides.models import Ride, RideStatusHistory


@shared_task(name="apps.rides.tasks.expire_unassigned_mobility_requests")
def expire_unassigned_mobility_requests():
    """Expire stale unpaid requests; never silently abandon a paid job without refunds."""
    timeout_minutes = max(1, int(os.getenv("MOBILITY_REQUEST_TIMEOUT_MINUTES", "15")))
    cutoff = timezone.now() - timedelta(minutes=timeout_minutes)
    now = timezone.now()
    rides_expired = 0
    rides_cancelled = 0
    parcels_expired = 0
    parcels_cancelled = 0

    ride_ids = list(
        Ride.objects.filter(
            driver__isnull=True,
            status__in=(Ride.Status.REQUESTED, Ride.Status.SEARCHING),
            created_at__lte=cutoff,
        )
        .exclude(payment_status=Ride.PaymentStatus.PENDING)
        .values_list("pk", flat=True)
    )
    for ride_id in ride_ids:
        with transaction.atomic():
            ride = Ride.objects.select_for_update().filter(pk=ride_id).first()
            if (
                ride is None
                or ride.driver_id is not None
                or ride.status not in (Ride.Status.REQUESTED, Ride.Status.SEARCHING)
                or ride.created_at > cutoff
                or ride.payment_status == Ride.PaymentStatus.PENDING
            ):
                continue
            if ride.payment_method == Ride.PaymentMethod.ONLINE and ride.payment_status == Ride.PaymentStatus.PAID:
                # A refund workflow is required before automatically closing paid jobs.
                continue
            if ride.payment_method == Ride.PaymentMethod.ONLINE:
                ride.status = Ride.Status.CANCELLED
                ride.cancelled_at = now
                rides_cancelled += 1
                note = "Request expired before online payment was completed."
                title = "Ride request expired"
                message = "Your unpaid ride request expired. You can create a new request."
            else:
                ride.status = Ride.Status.NO_DRIVER
                rides_expired += 1
                note = "No driver accepted the request before the dispatch timeout."
                title = "No driver available"
                message = "No driver accepted your ride request in time. Please try again."
            ride.save(update_fields=["status", "cancelled_at", "updated_at"])
            RideStatusHistory.objects.create(
                ride=ride, status=ride.status, changed_by=None, note=note
            )
            create_notification(
                user=ride.passenger,
                title=title,
                message=message,
                notification_type=Notification.Type.DELIVERY,
                data={"service": "RIDE", "ride_id": str(ride.pk), "status": ride.status},
            )

    parcel_ids = list(
        ParcelShipment.objects.filter(
            driver__isnull=True,
            status=ParcelShipment.Status.REQUESTED,
            created_at__lte=cutoff,
        )
        .exclude(payment_status=ParcelShipment.PaymentStatus.PENDING)
        .values_list("pk", flat=True)
    )
    for parcel_id in parcel_ids:
        with transaction.atomic():
            parcel = ParcelShipment.objects.select_for_update().filter(pk=parcel_id).first()
            if (
                parcel is None
                or parcel.driver_id is not None
                or parcel.status != ParcelShipment.Status.REQUESTED
                or parcel.created_at > cutoff
                or parcel.payment_status == ParcelShipment.PaymentStatus.PENDING
            ):
                continue
            if parcel.payment_method == ParcelShipment.PaymentMethod.ONLINE and parcel.payment_status == ParcelShipment.PaymentStatus.PAID:
                continue
            if parcel.payment_method == ParcelShipment.PaymentMethod.ONLINE:
                parcel.status = ParcelShipment.Status.CANCELLED
                parcel.cancelled_at = now
                parcels_cancelled += 1
                note = "Parcel request expired before online payment was completed."
                title = "Parcel request expired"
                message = "Your unpaid parcel request expired. Please create a new request."
            else:
                parcel.status = ParcelShipment.Status.NO_DRIVER
                parcels_expired += 1
                note = "No courier accepted the request before the dispatch timeout."
                title = "No courier available"
                message = "No courier accepted your parcel request in time. Please try again."
            parcel.save(update_fields=["status", "cancelled_at", "updated_at"])
            ParcelStatusHistory.objects.create(
                parcel=parcel, status=parcel.status, changed_by=None, note=note
            )
            create_notification(
                user=parcel.sender,
                title=title,
                message=message,
                notification_type=Notification.Type.DELIVERY,
                data={"service": "PARCEL", "parcel_id": str(parcel.pk), "status": parcel.status},
            )

    return {
        "rides_marked_no_driver": rides_expired,
        "rides_cancelled_unpaid": rides_cancelled,
        "parcels_marked_no_driver": parcels_expired,
        "parcels_cancelled_unpaid": parcels_cancelled,
    }
