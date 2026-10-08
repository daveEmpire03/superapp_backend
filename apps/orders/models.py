from django.conf import settings
from django.db import models

from core.models import TimeStampedModel
from apps.stores.models import Store
from apps.catalog.models import Product


class Order(TimeStampedModel):

    class Fulfilment(models.TextChoices):
        DELIVERY = "DELIVERY", "Delivery"
        PICKUP = "PICKUP", "Pickup"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        PREPARING = "PREPARING", "Preparing"
        READY = "READY", "Ready"
        DISPATCHED = "DISPATCHED", "Dispatched"
        OUT_FOR_DELIVERY = (
            "OUT_FOR_DELIVERY",
            "Out for delivery",
        )
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"

    class PaymentStatus(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    reference = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
    )

    fulfilment_type = models.CharField(
        max_length=12,
        choices=Fulfilment.choices,
    )

    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    payment_status = models.CharField(
        max_length=12,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
        db_index=True,
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    delivery_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    promotion_code = models.CharField(
        max_length=50,
        blank=True,
    )

    delivery_address_snapshot = models.JSONField(
        default=dict,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    reservation_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    inventory_committed = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "status"],
                name="order_user_status_idx",
            ),
            models.Index(
                fields=["payment_status"],
                name="order_payment_idx",
            ),
        ]

    def __str__(self):
        return self.reference


class OrderItem(TimeStampedModel):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
    )

    product_name = models.CharField(
        max_length=180,
    )

    sku = models.CharField(
        max_length=80,
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    quantity = models.PositiveIntegerField()

    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class OrderStatusHistory(TimeStampedModel):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history",
    )

    status = models.CharField(
        max_length=24,
        choices=Order.Status.choices,
    )

    note = models.CharField(
        max_length=255,
        blank=True,
    )

    def __str__(self):
        return f"{self.order.reference}: {self.status}"
