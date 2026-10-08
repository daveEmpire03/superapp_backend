from django.conf import settings
from django.db import models

from apps.orders.models import Order
from apps.stores.models import Store
from core.models import TimeStampedModel


class SupportTicket(TimeStampedModel):
    class Category(models.TextChoices):
        ORDER = "ORDER", "Order"
        PAYMENT = "PAYMENT", "Payment"
        DELIVERY = "DELIVERY", "Delivery"
        REFUND = "REFUND", "Refund"
        PRODUCT = "PRODUCT", "Product"
        ACCOUNT = "ACCOUNT", "Account"
        PROMOTION = "PROMOTION", "Promotion"
        OTHER = "OTHER", "Other"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        WAITING_CUSTOMER = "WAITING_CUSTOMER", "Waiting for Customer"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="support_tickets",
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="support_tickets",
    )

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
        db_index=True,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
        db_index=True,
    )

    subject = models.CharField(
        max_length=160,
    )

    message = models.TextField()

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_support_tickets",
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="supp_ticket_status_idx",
            ),
            models.Index(
                fields=["store", "status"],
                name="supp_ticket_store_idx",
            ),
            models.Index(
                fields=["user", "created_at"],
                name="supp_ticket_user_idx",
            ),
        ]

    def __str__(self):
        return f"{self.subject} - {self.status}"


class SupportMessage(TimeStampedModel):
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name="replies",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_messages",
    )

    message = models.TextField()

    is_staff_reply = models.BooleanField(
        default=False,
        db_index=True,
    )

    class Meta:
        ordering = ["created_at"]

        indexes = [
            models.Index(
                fields=["ticket", "created_at"],
                name="supp_msg_ticket_idx",
            ),
        ]

    def __str__(self):
        return f"Reply on {self.ticket_id}"


class SupportStatusHistory(TimeStampedModel):
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name="status_history",
    )

    from_status = models.CharField(
        max_length=30,
        blank=True,
    )

    to_status = models.CharField(
        max_length=30,
        choices=SupportTicket.Status.choices,
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_status_changes",
    )

    note = models.CharField(
        max_length=255,
        blank=True,
    )

    class Meta:
        ordering = ["created_at"]

        indexes = [
            models.Index(
                fields=["ticket", "created_at"],
                name="supp_hist_ticket_idx",
            ),
        ]

    def __str__(self):
        return f"{self.ticket_id}: " f"{self.from_status or 'NEW'} -> {self.to_status}"
