from django.conf import settings
from django.db import models

from apps.orders.models import Order
from core.models import TimeStampedModel


class LoyaltyEntry(TimeStampedModel):
    class Type(models.TextChoices):
        EARN = "EARN", "Earn"
        REDEEM = "REDEEM", "Redeem"
        REVERSAL = "REVERSAL", "Reversal"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="loyalty_entries",
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="loyalty_entries",
    )

    entry_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        db_index=True,
    )

    # Positive = credit.
    # Negative = debit.
    points = models.IntegerField()

    reason = models.CharField(
        max_length=160,
    )

    reference = models.CharField(
        max_length=120,
        blank=True,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_loyalty_entries",
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["user", "created_at"],
                name="loyalty_user_time_idx",
            ),
            models.Index(
                fields=["user", "entry_type"],
                name="loyalty_user_type_idx",
            ),
            models.Index(
                fields=["order", "entry_type"],
                name="loyalty_order_type_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user} - " f"{self.entry_type} - " f"{self.points}"
