from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class DeviceToken(TimeStampedModel):
    class Platform(models.TextChoices):
        ANDROID = "ANDROID", "Android"
        IOS = "IOS", "iOS"
        WEB = "WEB", "Web"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_tokens",
    )

    token = models.TextField(
        unique=True,
    )

    platform = models.CharField(
        max_length=20,
        choices=Platform.choices,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-updated_at"]

        indexes = [
            models.Index(
                fields=["user", "is_active"],
                name="device_user_active_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user} - " f"{self.platform}"


class Notification(TimeStampedModel):
    class Type(models.TextChoices):
        GENERAL = "GENERAL", "General"
        ORDER = "ORDER", "Order"
        PAYMENT = "PAYMENT", "Payment"
        DELIVERY = "DELIVERY", "Delivery"
        PROMOTION = "PROMOTION", "Promotion"
        LOYALTY = "LOYALTY", "Loyalty"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.GENERAL,
        db_index=True,
    )

    title = models.CharField(
        max_length=160,
    )

    message = models.TextField()

    data = models.JSONField(
        default=dict,
        blank=True,
    )

    is_read = models.BooleanField(
        default=False,
        db_index=True,
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "is_read",
                    "created_at",
                ],
                name="notif_user_read_time_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user} - " f"{self.title}"
