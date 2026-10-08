from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.catalog.models import Product
from core.models import TimeStampedModel


class Review(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ]
    )

    comment = models.TextField(
        blank=True,
        max_length=2000,
    )

    is_verified_purchase = models.BooleanField(
        default=False,
        db_index=True,
    )

    is_approved = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="unique_user_product_review",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    rating__gte=1,
                    rating__lte=5,
                ),
                name="review_rating_between_1_and_5",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "product",
                    "is_approved",
                    "created_at",
                ],
                name="review_product_approved_idx",
            ),
            models.Index(
                fields=[
                    "user",
                    "created_at",
                ],
                name="review_user_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user} - " f"{self.product} " f"({self.rating}/5)"
