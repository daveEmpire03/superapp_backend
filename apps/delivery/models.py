from django.conf import settings
from django.db import models

from apps.orders.models import Order
from core.models import TimeStampedModel


class Delivery(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ASSIGNED = "ASSIGNED", "Assigned"
        ACCEPTED = "ACCEPTED", "Accepted"
        PICKED_UP = "PICKED_UP", "Picked Up"
        OUT_FOR_DELIVERY = (
            "OUT_FOR_DELIVERY",
            "Out for Delivery",
        )
        DELIVERED = "DELIVERED", "Delivered"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    order = models.OneToOneField(
        Order,
        on_delete=models.PROTECT,
        related_name="delivery",
    )

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliveries",
        limit_choices_to={"role": "RIDER"},
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    assigned_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    picked_up_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    out_for_delivery_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    delivery_note = models.TextField(
        blank=True,
    )

    proof_note = models.CharField(
        max_length=255,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["rider", "status"],
                name="delivery_rider_status_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="delivery_status_time_idx",
            ),
        ]

    def __str__(self):
        return f"{self.order.reference} - " f"{self.get_status_display()}"


class DeliveryStatusHistory(TimeStampedModel):
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="status_history",
    )

    status = models.CharField(
        max_length=30,
        choices=Delivery.Status.choices,
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_status_changes",
    )

    note = models.CharField(
        max_length=255,
        blank=True,
    )

    class Meta:
        ordering = ["created_at"]

        indexes = [
            models.Index(
                fields=["delivery", "created_at"],
                name="delivery_hist_time_idx",
            ),
        ]

    def __str__(self):
        return f"{self.delivery.order.reference} - " f"{self.status}"
