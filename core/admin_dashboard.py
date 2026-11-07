from datetime import timedelta

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.inventory.models import StoreInventory
from apps.orders.models import Order


def dashboard_callback(request, context):
    """Build permission-aware, read-only dashboard metrics from live records."""
    can_view_orders = request.user.has_perm("orders.view_order")
    can_view_customers = request.user.has_perm("accounts.view_user")
    can_view_products = request.user.has_perm("catalog.view_product")
    can_view_inventory = request.user.has_perm("inventory.view_storeinventory")

    now = timezone.now()
    start_date = timezone.localdate() - timedelta(days=6)
    start_datetime = now - timedelta(days=7)

    context.update({
        "dashboard_generated_at": now,
        "orders_count": None,
        "pending_orders_count": None,
        "paid_revenue": None,
        "weekly_revenue": None,
        "customers_count": None,
        "active_products_count": None,
        "low_stock_count": None,
        "weekly_order_points": [],
        "recent_orders": [],
    })

    if can_view_orders:
        orders = Order.objects.all()
        paid_orders = orders.filter(payment_status=Order.PaymentStatus.PAID)
        context["orders_count"] = orders.count()
        context["pending_orders_count"] = orders.filter(
            status__in=(
                Order.Status.PENDING,
                Order.Status.CONFIRMED,
                Order.Status.PREPARING,
            )
        ).count()
        context["paid_revenue"] = paid_orders.aggregate(total=Sum("total"))["total"] or 0
        context["weekly_revenue"] = (
            paid_orders.filter(created_at__gte=start_datetime)
            .aggregate(total=Sum("total"))["total"] or 0
        )
        context["recent_orders"] = (
            orders.select_related("user", "store").order_by("-created_at")[:8]
        )

        daily_rows = (
            orders.filter(created_at__gte=start_datetime)
            .annotate(
                day=TruncDate(
                    "created_at", tzinfo=timezone.get_current_timezone()
                )
            )
            .values("day")
            .annotate(
                order_count=Count("id"),
                paid_total=Sum(
                    "total",
                    filter=Q(payment_status=Order.PaymentStatus.PAID),
                ),
            )
            .order_by("day")
        )
        daily_map = {row["day"]: row for row in daily_rows}
        days = [start_date + timedelta(days=index) for index in range(7)]
        counts = [daily_map.get(day, {}).get("order_count", 0) for day in days]
        max_count = max(counts, default=0)
        context["weekly_order_points"] = [
            {
                "label": day.strftime("%a"),
                "orders": counts[index],
                "bar_height": (
                    round((counts[index] / max_count) * 100) if max_count else 0
                ),
                "revenue": daily_map.get(day, {}).get("paid_total") or 0,
            }
            for index, day in enumerate(days)
        ]

    if can_view_customers:
        context["customers_count"] = User.objects.filter(
            role=User.Role.CUSTOMER
        ).count()

    if can_view_products:
        context["active_products_count"] = Product.objects.filter(
            is_active=True
        ).count()

    if can_view_inventory:
        context["low_stock_count"] = (
            StoreInventory.objects.filter(is_available=True)
            .annotate(
                _available_quantity=F("quantity") - F("reserved_quantity")
            )
            .filter(_available_quantity__lte=F("low_stock_threshold"))
            .count()
        )

    return context
