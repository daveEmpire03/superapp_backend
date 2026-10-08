from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.orders.models import (
    Order,
    OrderStatusHistory,
)

from .models import (
    Delivery,
    DeliveryStatusHistory,
)


RIDER_TRANSITIONS = {
    Delivery.Status.ASSIGNED: {
        Delivery.Status.ACCEPTED,
        Delivery.Status.REJECTED,
    },
    Delivery.Status.ACCEPTED: {
        Delivery.Status.PICKED_UP,
    },
    Delivery.Status.PICKED_UP: {
        Delivery.Status.OUT_FOR_DELIVERY,
    },
    Delivery.Status.OUT_FOR_DELIVERY: {
        Delivery.Status.DELIVERED,
    },
}


def _record_history(
    *,
    delivery,
    status,
    changed_by=None,
    note="",
):
    DeliveryStatusHistory.objects.create(
        delivery=delivery,
        status=status,
        changed_by=changed_by,
        note=note,
    )


@transaction.atomic
def assign_rider(
    *,
    delivery_id,
    rider,
    assigned_by,
):
    delivery = (
        Delivery.objects.select_for_update().select_related("order").get(id=delivery_id)
    )

    order = Order.objects.select_for_update().get(id=delivery.order_id)

    if order.fulfilment_type != Order.Fulfilment.DELIVERY:
        raise ValidationError(
            {"delivery": "Pickup orders cannot be assigned " "to a rider."}
        )

    if order.payment_status != Order.PaymentStatus.PAID:
        raise ValidationError(
            {"delivery": "The order must be paid before " "a rider can be assigned."}
        )

    if order.status in {
        Order.Status.CANCELLED,
        Order.Status.EXPIRED,
        Order.Status.DELIVERED,
    }:
        raise ValidationError(
            {"delivery": "This order cannot be assigned " "for delivery."}
        )

    if delivery.status in {
        Delivery.Status.PICKED_UP,
        Delivery.Status.OUT_FOR_DELIVERY,
        Delivery.Status.DELIVERED,
        Delivery.Status.CANCELLED,
    }:
        raise ValidationError(
            {"delivery": "The rider cannot be changed " "at this stage."}
        )

    delivery.rider = rider
    delivery.status = Delivery.Status.ASSIGNED
    delivery.assigned_at = timezone.now()

    # Reset timestamps belonging to a previous
    # rejected assignment.
    delivery.accepted_at = None

    delivery.save(
        update_fields=[
            "rider",
            "status",
            "assigned_at",
            "accepted_at",
            "updated_at",
        ]
    )

    _record_history(
        delivery=delivery,
        status=Delivery.Status.ASSIGNED,
        changed_by=assigned_by,
        note=(f"Delivery assigned to " f"{rider.get_full_name() or rider.username}."),
    )

    return delivery


@transaction.atomic
def update_rider_delivery_status(
    *,
    delivery_id,
    rider,
    new_status,
    note="",
    proof_note="",
):
    delivery = (
        Delivery.objects.select_for_update()
        .select_related(
            "order",
            "order__store",
        )
        .get(
            id=delivery_id,
            rider=rider,
        )
    )

    order = Order.objects.select_for_update().get(id=delivery.order_id)

    allowed = RIDER_TRANSITIONS.get(
        delivery.status,
        set(),
    )

    if new_status not in allowed:
        raise ValidationError(
            {
                "status": (
                    f"Cannot move delivery from "
                    f"{delivery.status} to "
                    f"{new_status}."
                )
            }
        )

    now = timezone.now()

    if new_status == Delivery.Status.ACCEPTED:
        delivery.status = new_status
        delivery.accepted_at = now

        delivery.save(
            update_fields=[
                "status",
                "accepted_at",
                "updated_at",
            ]
        )

    elif new_status == Delivery.Status.REJECTED:
        delivery.status = new_status

        delivery.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    elif new_status == Delivery.Status.PICKED_UP:
        if order.status not in {
            Order.Status.READY,
            Order.Status.DISPATCHED,
        }:
            raise ValidationError(
                {"order": ("The store must mark the order " "ready before pickup.")}
            )

        delivery.status = new_status
        delivery.picked_up_at = now

        if order.status == Order.Status.READY:
            order.status = Order.Status.DISPATCHED

            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            OrderStatusHistory.objects.create(
                order=order,
                status=Order.Status.DISPATCHED,
                note="Order collected by rider.",
            )

        delivery.save(
            update_fields=[
                "status",
                "picked_up_at",
                "updated_at",
            ]
        )

    elif new_status == Delivery.Status.OUT_FOR_DELIVERY:
        delivery.status = new_status
        delivery.out_for_delivery_at = now

        order.status = Order.Status.OUT_FOR_DELIVERY

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        OrderStatusHistory.objects.create(
            order=order,
            status=Order.Status.OUT_FOR_DELIVERY,
            note="Order is out for delivery.",
        )

        delivery.save(
            update_fields=[
                "status",
                "out_for_delivery_at",
                "updated_at",
            ]
        )

    elif new_status == Delivery.Status.DELIVERED:
        delivery.status = new_status
        delivery.delivered_at = now
        delivery.proof_note = proof_note

        order.status = Order.Status.DELIVERED

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        OrderStatusHistory.objects.create(
            order=order,
            status=Order.Status.DELIVERED,
            note="Order delivered to customer.",
        )

        delivery.save(
            update_fields=[
                "status",
                "delivered_at",
                "proof_note",
                "updated_at",
            ]
        )

    _record_history(
        delivery=delivery,
        status=new_status,
        changed_by=rider,
        note=note,
    )

    return delivery


@transaction.atomic
def cancel_delivery(
    *,
    delivery_id,
    cancelled_by,
    reason="",
):
    delivery = (
        Delivery.objects.select_for_update().select_related("order").get(id=delivery_id)
    )

    if delivery.status == Delivery.Status.DELIVERED:
        raise ValidationError(
            {"delivery": "A delivered delivery cannot " "be cancelled."}
        )

    if delivery.status == Delivery.Status.CANCELLED:
        return delivery

    delivery.status = Delivery.Status.CANCELLED
    delivery.cancelled_at = timezone.now()

    delivery.save(
        update_fields=[
            "status",
            "cancelled_at",
            "updated_at",
        ]
    )

    _record_history(
        delivery=delivery,
        status=Delivery.Status.CANCELLED,
        changed_by=cancelled_by,
        note=reason or "Delivery cancelled.",
    )

    return delivery
