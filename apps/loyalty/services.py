from decimal import Decimal, ROUND_DOWN

from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from .models import LoyaltyEntry


# Bokku Mart loyalty earning rule.
# Every NGN 100 of eligible merchandise spend
# earns 1 loyalty point.
NAIRA_PER_POINT = Decimal("100.00")


def get_loyalty_balance(user):
    result = LoyaltyEntry.objects.filter(user=user).aggregate(total=Sum("points"))

    return result["total"] or 0


def calculate_order_points(order):
    """
    Calculate loyalty points for a completed order.

    Eligible spend:
        subtotal - discount

    Delivery fees do not earn loyalty points.
    Partial points are discarded.
    """

    eligible_amount = Decimal(order.subtotal) - Decimal(order.discount)

    if eligible_amount <= Decimal("0.00"):
        return 0

    points = (eligible_amount / NAIRA_PER_POINT).quantize(
        Decimal("1"),
        rounding=ROUND_DOWN,
    )

    return int(points)


@transaction.atomic
def earn_points(
    *,
    user,
    points,
    reason,
    order=None,
    reference="",
):
    points = int(points)

    if points <= 0:
        raise ValidationError({"points": "Earned points must be " "greater than zero."})

    # Lock the user so concurrent loyalty
    # operations for this customer are serialized.
    user_model = type(user)

    user_model.objects.select_for_update().get(pk=user.pk)

    if order is not None:
        existing = LoyaltyEntry.objects.filter(
            user=user,
            order=order,
            entry_type=(LoyaltyEntry.Type.EARN),
        ).first()

        if existing:
            return existing

    return LoyaltyEntry.objects.create(
        user=user,
        order=order,
        entry_type=LoyaltyEntry.Type.EARN,
        points=points,
        reason=reason,
        reference=reference,
    )


@transaction.atomic
def award_order_points(order):
    """
    Award loyalty points for a delivered order.

    Idempotent:
    an order can only receive one EARN entry.
    """

    if order.status != order.Status.DELIVERED:
        raise ValidationError(
            {"order": "Loyalty points can only be " "awarded to delivered orders."}
        )

    if order.payment_status != order.PaymentStatus.PAID:
        raise ValidationError(
            {"order": "Loyalty points cannot be " "awarded to an unpaid order."}
        )

    existing = LoyaltyEntry.objects.filter(
        order=order,
        entry_type=LoyaltyEntry.Type.EARN,
    ).first()

    if existing:
        return existing

    points = calculate_order_points(order)

    # Very small orders may legitimately earn
    # zero points.
    if points <= 0:
        return None

    return earn_points(
        user=order.user,
        points=points,
        order=order,
        reason="Points earned from delivered order.",
        reference=order.reference,
    )


@transaction.atomic
def redeem_points(
    *,
    user,
    points,
    reason,
    order=None,
    reference="",
):
    points = int(points)

    if points <= 0:
        raise ValidationError(
            {"points": "Redeemed points must be " "greater than zero."}
        )

    user_model = type(user)

    user_model.objects.select_for_update().get(pk=user.pk)

    balance = get_loyalty_balance(user)

    if points > balance:
        raise ValidationError({"points": "Insufficient loyalty points."})

    return LoyaltyEntry.objects.create(
        user=user,
        order=order,
        entry_type=(LoyaltyEntry.Type.REDEEM),
        points=-points,
        reason=reason,
        reference=reference,
    )


@transaction.atomic
def reverse_order_points(
    *,
    order,
    reason="Order loyalty points reversed.",
    created_by=None,
):
    earning = LoyaltyEntry.objects.filter(
        order=order,
        entry_type=LoyaltyEntry.Type.EARN,
    ).first()

    if earning is None:
        return None

    existing_reversal = LoyaltyEntry.objects.filter(
        order=order,
        entry_type=(LoyaltyEntry.Type.REVERSAL),
    ).first()

    if existing_reversal:
        return existing_reversal

    return LoyaltyEntry.objects.create(
        user=earning.user,
        order=order,
        entry_type=(LoyaltyEntry.Type.REVERSAL),
        points=-earning.points,
        reason=reason,
        reference=order.reference,
        created_by=created_by,
    )


@transaction.atomic
def adjust_points(
    *,
    user,
    points,
    reason,
    created_by,
    reference="",
):
    points = int(points)

    if points == 0:
        raise ValidationError({"points": "Adjustment cannot be zero."})

    user_model = type(user)

    user_model.objects.select_for_update().get(pk=user.pk)

    if points < 0:
        balance = get_loyalty_balance(user)

        if abs(points) > balance:
            raise ValidationError(
                {"points": "Adjustment would make " "the loyalty balance negative."}
            )

    return LoyaltyEntry.objects.create(
        user=user,
        entry_type=(LoyaltyEntry.Type.ADJUSTMENT),
        points=points,
        reason=reason,
        reference=reference,
        created_by=created_by,
    )
