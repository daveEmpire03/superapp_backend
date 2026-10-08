from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class Store(TimeStampedModel):
    name = models.CharField(max_length=160)
    code = models.SlugField(unique=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
    )

    opens_at = models.TimeField(
        null=True,
        blank=True,
    )
    closes_at = models.TimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)
    supports_delivery = models.BooleanField(default=True)
    supports_pickup = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.city}"


class StoreStaffMembership(TimeStampedModel):

    class Role(models.TextChoices):
        MANAGER = "MANAGER", "Manager"
        STAFF = "STAFF", "Staff"

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="staff_memberships",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="store_memberships",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STAFF,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["store", "user"],
                name="unique_store_staff_membership",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "is_active",
                ],
                name="storestaff_user_active_idx",
            ),
            models.Index(
                fields=[
                    "store",
                    "is_active",
                ],
                name="storestaff_store_active_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.store.name} ({self.role})"
