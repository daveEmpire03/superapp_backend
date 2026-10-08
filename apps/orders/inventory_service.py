from apps.inventory.models import (
    InventoryMovement,
    StoreInventory,
)


class InventoryReservationError(Exception):
    """
    Raised when reserved inventory state
    is inconsistent.
    """


def _get_locked_inventory(order):
    """
    Load and lock inventory rows belonging
    to an order.

    Caller must:
    1. be inside transaction.atomic()
    2. already hold a SELECT FOR UPDATE
       lock on the Order
    """

    order_items = list(order.items.select_related("product").all())

    product_ids = [item.product_id for item in order_items]

    inventories = {
        inventory.product_id: inventory
        for inventory in (
            StoreInventory.objects.select_for_update().filter(
                store_id=order.store_id,
                product_id__in=product_ids,
            )
        )
    }

    return (
        order_items,
        inventories,
    )


def commit_reserved_inventory(
    order,
    *,
    performed_by=None,
):
    """
    Convert reserved inventory into sold stock.

    The caller must hold the Order row lock.

    Idempotency is controlled by
    order.inventory_committed.
    """

    if order.inventory_committed:
        return

    order_items, inventories = _get_locked_inventory(order)

    for item in order_items:
        inventory = inventories.get(item.product_id)

        if inventory is None:
            raise InventoryReservationError(
                "Inventory record missing for " f"{item.product_name}."
            )

        if inventory.reserved_quantity < item.quantity:
            raise InventoryReservationError(
                "Reserved inventory is " "inconsistent for " f"{item.product_name}."
            )

        if inventory.quantity < item.quantity:
            raise InventoryReservationError(
                "Physical inventory is " "inconsistent for " f"{item.product_name}."
            )

        quantity_before = inventory.quantity

        reserved_before = inventory.reserved_quantity

        inventory.reserved_quantity -= item.quantity

        inventory.quantity -= item.quantity

        inventory.save(
            update_fields=[
                "quantity",
                "reserved_quantity",
                "updated_at",
            ]
        )

        InventoryMovement.objects.create(
            inventory=inventory,
            movement_type=(InventoryMovement.Type.SALE),
            quantity_change=(-item.quantity),
            quantity_before=(quantity_before),
            quantity_after=(inventory.quantity),
            reserved_before=(reserved_before),
            reserved_after=(inventory.reserved_quantity),
            reason=("Reserved stock committed " "after successful payment."),
            performed_by=performed_by,
            reference=order.reference,
        )

    order.inventory_committed = True


def release_reserved_inventory(
    order,
    *,
    performed_by=None,
    reason=("Checkout inventory reservation " "released."),
):
    """
    Release inventory reserved by an
    unpaid checkout.

    Physical quantity does not change.

    Must never be used to reverse stock
    belonging to a successfully paid order.
    """

    if order.inventory_committed:
        raise InventoryReservationError(
            "Committed inventory cannot be " "released as an unpaid reservation."
        )

    order_items, inventories = _get_locked_inventory(order)

    for item in order_items:
        inventory = inventories.get(item.product_id)

        if inventory is None:
            raise InventoryReservationError(
                "Inventory record missing for " f"{item.product_name}."
            )

        if inventory.reserved_quantity < item.quantity:
            raise InventoryReservationError(
                "Reserved inventory is " "inconsistent for " f"{item.product_name}."
            )

        reserved_before = inventory.reserved_quantity

        inventory.reserved_quantity -= item.quantity

        inventory.save(
            update_fields=[
                "reserved_quantity",
                "updated_at",
            ]
        )

        InventoryMovement.objects.create(
            inventory=inventory,
            movement_type=(InventoryMovement.Type.RESERVATION_RELEASE),
            # Physical stock remains unchanged.
            quantity_change=0,
            quantity_before=(inventory.quantity),
            quantity_after=(inventory.quantity),
            reserved_before=(reserved_before),
            reserved_after=(inventory.reserved_quantity),
            reason=reason,
            performed_by=performed_by,
            reference=order.reference,
        )
