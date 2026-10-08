from celery import shared_task

from django.db import transaction
from django.utils import timezone

from apps.promotions.models import (
    PromotionRedemption,
)

from .inventory_service import (
    release_reserved_inventory,
)
from .models import (
    Order,
    OrderStatusHistory,
)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def expire_order_reservation(
    self,
    order_id,
):
    """
    Expire one unpaid checkout and release its
    reserved inventory and promotion usage.

    Safe to execute more than once.
    """

    with transaction.atomic():
        try:
            order = Order.objects.select_for_update().get(id=order_id)

        except Order.DoesNotExist:
            return {
                "status": "not_found",
                "order_id": str(order_id),
            }

        if (
            order.payment_status == Order.PaymentStatus.PAID
            or order.inventory_committed
        ):
            return {
                "status": "paid",
                "order_id": str(order.id),
            }

        if order.status in {
            Order.Status.EXPIRED,
            Order.Status.CANCELLED,
        }:
            return {
                "status": "already_terminal",
                "order_id": str(order.id),
            }

        if not order.reservation_expires_at:
            return {
                "status": "no_expiration",
                "order_id": str(order.id),
            }

        if order.reservation_expires_at > timezone.now():
            return {
                "status": "not_due",
                "order_id": str(order.id),
            }

        release_reserved_inventory(
            order,
            reason=("Checkout reservation expired " "before payment."),
        )

        # The checkout was never paid, so its
        # promotion usage must become available
        # again.
        PromotionRedemption.objects.filter(order=order).delete()

        order.status = Order.Status.EXPIRED

        order.reservation_expires_at = None

        order.save(
            update_fields=[
                "status",
                "reservation_expires_at",
                "updated_at",
            ]
        )

        OrderStatusHistory.objects.create(
            order=order,
            status=Order.Status.EXPIRED,
            note=("Checkout expired before " "payment was completed."),
        )

        return {
            "status": "expired",
            "order_id": str(order.id),
        }


@shared_task
def expire_due_order_reservations():
    """
    Find expired checkout reservations.

    Each order is processed by its own task so that
    one transaction does not lock many orders.
    """

    now = timezone.now()

    order_ids = list(
        Order.objects.filter(
            status=Order.Status.PENDING,
            payment_status__in=[
                Order.PaymentStatus.UNPAID,
                Order.PaymentStatus.FAILED,
            ],
            inventory_committed=False,
            reservation_expires_at__isnull=False,
            reservation_expires_at__lte=now,
        ).values_list("id", flat=True,)[:500]
    )

    for order_id in order_ids:
        expire_order_reservation.delay(str(order_id))

    return {
        "dispatched": len(order_ids),
    }
