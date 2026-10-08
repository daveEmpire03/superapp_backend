from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Promotion, PromotionRedemption


MONEY_PLACES = Decimal("0.01")


def normalize_code(code):
    if not code:
        return ""

    return str(code).strip().upper()


def calculate_discount(*, promotion, subtotal):
    subtotal = Decimal(subtotal)

    if promotion.discount_type == Promotion.DiscountType.PERCENT:
        discount = subtotal * promotion.value / Decimal("100")

    elif promotion.discount_type == Promotion.DiscountType.FIXED:
        discount = promotion.value

    else:
        raise ValidationError({"promotion_code": "Unsupported promotion type."})

    if promotion.max_discount_amount is not None:
        discount = min(
            discount,
            promotion.max_discount_amount,
        )

    discount = min(discount, subtotal)

    return discount.quantize(
        MONEY_PLACES,
        rounding=ROUND_HALF_UP,
    )


def validate_promotion(
    *,
    code,
    user,
    store,
    subtotal,
    lock=False,
):
    normalized_code = normalize_code(code)

    if not normalized_code:
        raise ValidationError({"promotion_code": "Promotion code is required."})

    subtotal = Decimal(subtotal)
    now = timezone.now()

    queryset = Promotion.objects.all()

    if lock:
        queryset = queryset.select_for_update()

    try:
        promotion = queryset.get(code__iexact=normalized_code)

    except Promotion.DoesNotExist:
        raise ValidationError({"promotion_code": "Invalid promotion code."})

    if not promotion.is_active:
        raise ValidationError({"promotion_code": "This promotion is inactive."})

    if promotion.starts_at > now:
        raise ValidationError({"promotion_code": "This promotion has not started yet."})

    if promotion.ends_at < now:
        raise ValidationError({"promotion_code": "This promotion has expired."})

    if promotion.store_id is not None and promotion.store_id != store.id:
        raise ValidationError(
            {"promotion_code": "This promotion is not valid " "for this store."}
        )

    if subtotal < promotion.min_order_amount:
        raise ValidationError(
            {
                "promotion_code": (
                    "Minimum order amount for this "
                    "promotion is "
                    f"{promotion.min_order_amount}."
                )
            }
        )

    if promotion.usage_limit is not None:
        total_usage = PromotionRedemption.objects.filter(promotion=promotion).count()

        if total_usage >= promotion.usage_limit:
            raise ValidationError(
                {"promotion_code": "This promotion has reached " "its usage limit."}
            )

    user_usage = PromotionRedemption.objects.filter(
        promotion=promotion,
        user=user,
    ).count()

    if user_usage >= promotion.per_user_limit:
        raise ValidationError(
            {
                "promotion_code": "You have reached the usage "
                "limit for this promotion."
            }
        )

    discount = calculate_discount(
        promotion=promotion,
        subtotal=subtotal,
    )

    return promotion, discount


@transaction.atomic
def redeem_promotion(
    *,
    promotion,
    user,
    order,
    discount_amount,
):
    promotion = Promotion.objects.select_for_update().get(id=promotion.id)

    existing = PromotionRedemption.objects.filter(order=order).first()

    if existing:
        if existing.promotion_id != promotion.id:
            raise ValidationError(
                {"promotion": "This order already has a " "different promotion."}
            )

        return existing

    if promotion.usage_limit is not None:
        total_usage = PromotionRedemption.objects.filter(promotion=promotion).count()

        if total_usage >= promotion.usage_limit:
            raise ValidationError(
                {"promotion": "This promotion has reached " "its usage limit."}
            )

    user_usage = PromotionRedemption.objects.filter(
        promotion=promotion,
        user=user,
    ).count()

    if user_usage >= promotion.per_user_limit:
        raise ValidationError(
            {"promotion": "The user has reached the " "promotion usage limit."}
        )

    return PromotionRedemption.objects.create(
        promotion=promotion,
        user=user,
        order=order,
        discount_amount=discount_amount,
    )


def available_promotions_for_store(store):
    now = timezone.now()

    return (
        Promotion.objects.filter(
            is_active=True,
            starts_at__lte=now,
            ends_at__gte=now,
        )
        .filter(Q(store__isnull=True) | Q(store=store))
        .select_related("store")
        .order_by("ends_at")
    )


# Backward-compatible helper for any older code
# that may still call discount_for().
def discount_for(code, subtotal):
    if not code:
        return Decimal("0.00")

    normalized_code = normalize_code(code)
    now = timezone.now()

    try:
        promotion = Promotion.objects.get(
            code__iexact=normalized_code,
            is_active=True,
            starts_at__lte=now,
            ends_at__gte=now,
        )
    except Promotion.DoesNotExist:
        raise ValueError("Invalid or expired promotion code.")

    subtotal = Decimal(subtotal)

    if subtotal < promotion.min_order_amount:
        raise ValueError("Order does not meet promotion minimum.")

    return calculate_discount(
        promotion=promotion,
        subtotal=subtotal,
    )
