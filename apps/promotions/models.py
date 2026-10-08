from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.orders.models import Order
from apps.stores.models import Store
from core.models import TimeStampedModel


class Promotion(TimeStampedModel):
    class DiscountType(models.TextChoices):
        PERCENT = "PERCENT", "Percent"
        FIXED = "FIXED", "Fixed"

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    title = models.CharField(
        max_length=160,
    )

    description = models.TextField(
        blank=True,
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="promotions",
        help_text=("Leave empty for a platform-wide promotion."),
    )

    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
    )

    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    min_order_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    max_discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    starts_at = models.DateTimeField()

    ends_at = models.DateTimeField()

    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=("Maximum total redemptions. " "Leave empty for unlimited."),
    )

    per_user_limit = models.PositiveIntegerField(
        default=1,
        help_text=("Maximum number of times one user " "can redeem this promotion."),
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "is_active",
                    "starts_at",
                    "ends_at",
                ],
                name="promo_active_period_idx",
            ),
            models.Index(
                fields=["store", "is_active"],
                name="promo_store_active_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.title}"


class PromotionRedemption(TimeStampedModel):
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.PROTECT,
        related_name="redemptions",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="promotion_redemptions",
    )

    order = models.OneToOneField(
        Order,
        on_delete=models.PROTECT,
        related_name="promotion_redemption",
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["promotion", "user"],
                name="promo_redemption_user_idx",
            ),
            models.Index(
                fields=["promotion", "created_at"],
                name="promo_redemption_time_idx",
            ),
        ]

    def __str__(self):
        return f"{self.promotion.code} - " f"{self.order.reference}"
