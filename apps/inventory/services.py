from django.core.exceptions import ValidationError
from django.db import transaction

from .models import InventoryMovement, StoreInventory


@transaction.atomic
def create_initial_inventory(
    *,
    store,
    product,
    price,
    quantity,
    performed_by=None,
    compare_at_price=None,
    low_stock_threshold=5,
    is_available=True,
):
    """
    Create the initial inventory record for a product at a store
    and record the corresponding stock movement.
    """

    if quantity < 0:
        raise ValidationError("Initial stock quantity cannot be negative.")

    if price < 0:
        raise ValidationError("Price cannot be negative.")

    if compare_at_price is not None and compare_at_price < 0:
        raise ValidationError("Compare-at price cannot be negative.")

    if StoreInventory.objects.filter(
        store=store,
        product=product,
    ).exists():
        raise ValidationError(
            "Inventory already exists for this product at this store."
        )

    inventory = StoreInventory.objects.create(
        store=store,
        product=product,
        price=price,
        compare_at_price=compare_at_price,
        quantity=quantity,
        reserved_quantity=0,
        low_stock_threshold=low_stock_threshold,
        is_available=is_available,
    )

    if quantity > 0:
        InventoryMovement.objects.create(
            inventory=inventory,
            movement_type=InventoryMovement.Type.INITIAL_STOCK,
            quantity_change=quantity,
            quantity_before=0,
            quantity_after=quantity,
            reserved_before=0,
            reserved_after=0,
            reason="Initial inventory stock",
            performed_by=performed_by,
            reference=f"INITIAL-{inventory.id}",
        )

    return inventory
