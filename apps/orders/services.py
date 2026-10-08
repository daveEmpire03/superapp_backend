import secrets
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.cart.models import Cart
from apps.inventory.models import (
    InventoryMovement,
    StoreInventory,
)
from apps.promotions.services import (
    redeem_promotion,
    validate_promotion,
)

from .models import (
    Order,
    OrderItem,
    OrderStatusHistory,
)


RESERVATION_MINUTES = 15


def generate_order_reference():
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")

    random_part = secrets.token_hex(3).upper()

    return f"BKM-{timestamp}-{random_part}"


def calculate_delivery_fee(
    fulfilment_type,
):
    if fulfilment_type == Order.Fulfilment.PICKUP:
        return Decimal("0.00")

    # Temporary rule.
    # Later this becomes distance/zone based.
    return Decimal("1000.00")


@transaction.atomic
def create_checkout(
    *,
    user,
    fulfilment_type,
    delivery_address=None,
    notes="",
    promotion_code="",
):
    try:
        cart = Cart.objects.select_for_update().select_related("store").get(user=user)

    except Cart.DoesNotExist:
        raise ValidationError({"cart": "Your cart is empty."})

    cart_items = list(
        cart.items.select_related(
            "inventory",
            "inventory__product",
        ).all()
    )

    if not cart_items:
        raise ValidationError({"cart": "Your cart is empty."})

    if cart.store_id is None:
        raise ValidationError({"store": "The cart does not have a store."})

    if fulfilment_type == Order.Fulfilment.DELIVERY and not delivery_address:
        raise ValidationError({"delivery_address": "A delivery address is required."})

    inventory_ids = [item.inventory_id for item in cart_items]

    locked_inventory = {
        inventory.id: inventory
        for inventory in (
            StoreInventory.objects.select_for_update()
            .select_related(
                "product",
                "store",
            )
            .filter(id__in=inventory_ids)
        )
    }

    subtotal = Decimal("0.00")
    order_lines = []

    for cart_item in cart_items:
        inventory = locked_inventory.get(cart_item.inventory_id)

        if inventory is None:
            raise ValidationError(
                {"cart": "One of the cart products " "is no longer available."}
            )

        if inventory.store_id != cart.store_id:
            raise ValidationError(
                {"cart": "Cart contains products " "from different stores."}
            )

        if (
            not inventory.is_available
            or not inventory.product.is_active
            or not inventory.store.is_active
        ):
            raise ValidationError(
                {"cart": (f"{inventory.product.name} " "is no longer available.")}
            )

        available_quantity = inventory.quantity - inventory.reserved_quantity

        if cart_item.quantity > available_quantity:
            raise ValidationError(
                {
                    "cart": (
                        f"Only {available_quantity} "
                        f"unit(s) of "
                        f"{inventory.product.name} "
                        "are currently available."
                    )
                }
            )

        line_total = inventory.price * cart_item.quantity

        subtotal += line_total

        order_lines.append(
            {
                "inventory": inventory,
                "product": inventory.product,
                "quantity": cart_item.quantity,
                "unit_price": inventory.price,
                "line_total": line_total,
            }
        )

    subtotal = subtotal.quantize(Decimal("0.01"))

    promotion = None
    discount = Decimal("0.00")

    normalized_promotion_code = promotion_code.strip().upper() if promotion_code else ""

    if normalized_promotion_code:
        promotion, discount = validate_promotion(
            code=normalized_promotion_code,
            user=user,
            store=cart.store,
            subtotal=subtotal,
            lock=True,
        )

    delivery_fee = calculate_delivery_fee(fulfilment_type)

    total = (subtotal - discount + delivery_fee).quantize(Decimal("0.01"))

    if total < Decimal("0.00"):
        total = Decimal("0.00")

    reservation_expires_at = timezone.now() + timedelta(minutes=RESERVATION_MINUTES)

    order = Order.objects.create(
        user=user,
        store=cart.store,
        reference=generate_order_reference(),
        fulfilment_type=fulfilment_type,
        status=Order.Status.PENDING,
        payment_status=(Order.PaymentStatus.UNPAID),
        subtotal=subtotal,
        discount=discount,
        delivery_fee=delivery_fee,
        total=total,
        promotion_code=(normalized_promotion_code),
        delivery_address_snapshot=(delivery_address or {}),
        notes=notes,
        reservation_expires_at=(reservation_expires_at),
    )

    if promotion is not None:
        redeem_promotion(
            promotion=promotion,
            user=user,
            order=order,
            discount_amount=discount,
        )

    order_items = []

    for line in order_lines:
        inventory = line["inventory"]

        quantity_before = inventory.quantity
        reserved_before = inventory.reserved_quantity

        inventory.reserved_quantity += line["quantity"]

        inventory.save(
            update_fields=[
                "reserved_quantity",
                "updated_at",
            ]
        )

        InventoryMovement.objects.create(
            inventory=inventory,
            movement_type=(InventoryMovement.Type.RESERVATION),
            quantity_change=0,
            quantity_before=quantity_before,
            quantity_after=inventory.quantity,
            reserved_before=reserved_before,
            reserved_after=(inventory.reserved_quantity),
            reason=("Inventory reserved during " "checkout."),
            performed_by=user,
            reference=order.reference,
        )

        order_items.append(
            OrderItem(
                order=order,
                product=line["product"],
                product_name=(line["product"].name),
                sku=line["product"].sku,
                unit_price=line["unit_price"],
                quantity=line["quantity"],
                line_total=line["line_total"],
            )
        )

    OrderItem.objects.bulk_create(order_items)

    OrderStatusHistory.objects.create(
        order=order,
        status=Order.Status.PENDING,
        note="Checkout created.",
    )

    # Only clear the cart after every checkout
    # operation succeeds.
    cart.items.all().delete()

    cart.store = None

    cart.save(
        update_fields=[
            "store",
            "updated_at",
        ]
    )

    return order
