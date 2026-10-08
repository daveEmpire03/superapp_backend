from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.catalog.models import Product
from apps.stores.models import Store
from core.models import TimeStampedModel


class StoreInventory(TimeStampedModel):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="inventory",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="store_inventory",
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    compare_at_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    quantity = models.PositiveIntegerField(
        default=0,
    )

    reserved_quantity = models.PositiveIntegerField(
        default=0,
    )

    low_stock_threshold = models.PositiveIntegerField(
        default=5,
    )

    is_available = models.BooleanField(
        default=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "store",
                    "product",
                ],
                name="unique_store_product",
            ),
            models.CheckConstraint(
                condition=models.Q(reserved_quantity__lte=models.F("quantity")),
                name=("inventory_reserved_not_above_quantity"),
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "store",
                    "is_available",
                ],
                name="inventory_store_available_idx",
            ),
            models.Index(
                fields=["product"],
                name="inventory_product_idx",
            ),
        ]

    def __str__(self):
        return f"{self.store.name} - " f"{self.product.name}"

    @property
    def available_quantity(self):
        return max(
            self.quantity - self.reserved_quantity,
            0,
        )

    @property
    def is_in_stock(self):
        return self.is_available and self.available_quantity > 0


class InventoryMovement(TimeStampedModel):

    class Type(models.TextChoices):
        INITIAL_STOCK = (
            "INITIAL_STOCK",
            "Initial Stock",
        )

        STOCK_IN = (
            "STOCK_IN",
            "Stock In",
        )

        STOCK_OUT = (
            "STOCK_OUT",
            "Stock Out",
        )

        RESERVATION = (
            "RESERVATION",
            "Reservation",
        )

        RESERVATION_RELEASE = (
            "RESERVATION_RELEASE",
            "Reservation Release",
        )

        SALE = (
            "SALE",
            "Sale",
        )

        ADJUSTMENT = (
            "ADJUSTMENT",
            "Adjustment",
        )

    inventory = models.ForeignKey(
        StoreInventory,
        on_delete=models.PROTECT,
        related_name="movements",
    )

    movement_type = models.CharField(
        max_length=30,
        choices=Type.choices,
    )

    # Signed quantity:
    # +10 means physical stock increased.
    # -3 means physical stock decreased.
    #
    # Reservation events may use the ordered
    # quantity while before/after fields preserve
    # the complete stock state.
    quantity_change = models.IntegerField()

    quantity_before = models.PositiveIntegerField()

    quantity_after = models.PositiveIntegerField()

    reserved_before = models.PositiveIntegerField(
        default=0,
    )

    reserved_after = models.PositiveIntegerField(
        default=0,
    )

    reason = models.CharField(
        max_length=255,
        blank=True,
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_movements",
    )

    reference = models.CharField(
        max_length=120,
        blank=True,
        db_index=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "inventory",
                    "created_at",
                ],
                name="inv_move_inventory_time_idx",
            ),
            models.Index(
                fields=[
                    "movement_type",
                    "created_at",
                ],
                name="inv_move_type_time_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.inventory} - " f"{self.movement_type} - " f"{self.quantity_change}"
        )
