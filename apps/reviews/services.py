from django.db.models import Avg, Count

from apps.orders.models import Order


def has_verified_purchase(*, user, product):
    if not user or not user.is_authenticated:
        return False

    return Order.objects.filter(
        user=user,
        status=Order.Status.DELIVERED,
        payment_status=Order.PaymentStatus.PAID,
        items__product=product,
    ).exists()


def get_product_rating_summary(product):
    summary = product.reviews.filter(
        is_approved=True,
    ).aggregate(
        average_rating=Avg("rating"),
        review_count=Count("id"),
    )

    average_rating = summary["average_rating"]

    return {
        "average_rating": (
            round(float(average_rating), 2) if average_rating is not None else 0.0
        ),
        "review_count": summary["review_count"],
    }
