from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import (
    Avg,
    Count,
    DecimalField,
    DurationField,
    ExpressionWrapper,
    F,
    IntegerField,
    Q,
    Sum,
)
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.delivery.models import Delivery
from apps.inventory.models import StoreInventory
from apps.orders.models import Order, OrderItem
from apps.stores.permissions import (
    get_managed_store_ids,
    is_platform_admin,
)


def _money(value):
    if value is None:
        value = Decimal("0.00")

    if not isinstance(value, Decimal):
        value = Decimal(str(value))

    return str(
        value.quantize(
            Decimal("0.01"),
        )
    )


def resolve_period(
    *,
    start_date=None,
    end_date=None,
):
    if end_date is None:
        end_date = timezone.localdate()

    if start_date is None:
        start_date = end_date - timedelta(days=29)

    current_timezone = timezone.get_current_timezone()

    start_datetime = timezone.make_aware(
        datetime.combine(
            start_date,
            time.min,
        ),
        current_timezone,
    )

    end_datetime = timezone.make_aware(
        datetime.combine(
            end_date,
            time.max,
        ),
        current_timezone,
    )

    return (
        start_date,
        end_date,
        start_datetime,
        end_datetime,
    )


def _ensure_store_access(
    *,
    user,
    store_id,
):
    if store_id is None:
        return

    if is_platform_admin(user):
        return

    managed_store_ids = get_managed_store_ids(user)

    if store_id not in managed_store_ids:
        raise PermissionDenied(
            "You do not have permission to view " "analytics for this store."
        )


def get_scoped_orders(
    *,
    user,
    start_date=None,
    end_date=None,
    store_id=None,
):
    (
        start_date,
        end_date,
        start_datetime,
        end_datetime,
    ) = resolve_period(
        start_date=start_date,
        end_date=end_date,
    )

    _ensure_store_access(
        user=user,
        store_id=store_id,
    )

    queryset = Order.objects.filter(
        created_at__gte=start_datetime,
        created_at__lte=end_datetime,
    )

    if store_id is not None:
        queryset = queryset.filter(
            store_id=store_id,
        )

    elif not is_platform_admin(user):
        managed_store_ids = get_managed_store_ids(user)

        queryset = queryset.filter(
            store_id__in=managed_store_ids,
        )

    return (
        queryset,
        start_date,
        end_date,
        start_datetime,
        end_datetime,
    )


def get_dashboard(
    *,
    user,
    start_date=None,
    end_date=None,
    store_id=None,
):
    (
        orders,
        start_date,
        end_date,
        start_datetime,
        end_datetime,
    ) = get_scoped_orders(
        user=user,
        start_date=start_date,
        end_date=end_date,
        store_id=store_id,
    )

    paid_orders = orders.filter(
        payment_status=Order.PaymentStatus.PAID,
    )

    financials = paid_orders.aggregate(
        revenue=Sum(
            "total",
            output_field=DecimalField(
                max_digits=16,
                decimal_places=2,
            ),
        ),
        average_order_value=Avg(
            "total",
            output_field=DecimalField(
                max_digits=16,
                decimal_places=2,
            ),
        ),
    )

    status_breakdown = list(
        orders.values("status")
        .annotate(
            count=Count("id"),
        )
        .order_by("status")
    )

    unique_customer_count = orders.values("user_id").distinct().count()

    new_customer_count = (
        orders.filter(
            user__date_joined__gte=start_datetime,
            user__date_joined__lte=end_datetime,
        )
        .values("user_id")
        .distinct()
        .count()
    )

    low_stock_count = get_low_stock_queryset(
        user=user,
        store_id=store_id,
    ).count()

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "orders": {
            "total": orders.count(),
            "paid": paid_orders.count(),
            "delivered": orders.filter(
                status=Order.Status.DELIVERED,
            ).count(),
            "cancelled": orders.filter(
                status=Order.Status.CANCELLED,
            ).count(),
            "status_breakdown": status_breakdown,
        },
        "revenue": {
            "total": _money(financials["revenue"]),
            "average_order_value": _money(financials["average_order_value"]),
        },
        "customers": {
            "unique_customers": unique_customer_count,
            "new_customers": new_customer_count,
        },
        "inventory": {
            "low_stock_items": low_stock_count,
        },
    }


def get_revenue_series(
    *,
    user,
    start_date=None,
    end_date=None,
    store_id=None,
):
    (
        orders,
        start_date,
        end_date,
        _,
        _,
    ) = get_scoped_orders(
        user=user,
        start_date=start_date,
        end_date=end_date,
        store_id=store_id,
    )

    rows = (
        orders.filter(
            payment_status=Order.PaymentStatus.PAID,
        )
        .annotate(
            day=TruncDate("created_at"),
        )
        .values("day")
        .annotate(
            revenue=Sum("total"),
            order_count=Count("id"),
        )
        .order_by("day")
    )

    data = []

    for row in rows:
        data.append(
            {
                "date": row["day"].isoformat(),
                "revenue": _money(row["revenue"]),
                "order_count": row["order_count"],
            }
        )

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "results": data,
    }


def get_top_products(
    *,
    user,
    start_date=None,
    end_date=None,
    store_id=None,
    limit=10,
):
    (
        orders,
        start_date,
        end_date,
        _,
        _,
    ) = get_scoped_orders(
        user=user,
        start_date=start_date,
        end_date=end_date,
        store_id=store_id,
    )

    rows = (
        OrderItem.objects.filter(
            order__in=orders,
            order__payment_status=(Order.PaymentStatus.PAID),
        )
        .values(
            "product_id",
            "product_name",
        )
        .annotate(
            units_sold=Sum("quantity"),
            revenue=Sum("line_total"),
            order_count=Count(
                "order_id",
                distinct=True,
            ),
        )
        .order_by(
            "-units_sold",
            "-revenue",
        )[:limit]
    )

    results = []

    for row in rows:
        results.append(
            {
                "product_id": (str(row["product_id"]) if row["product_id"] else None),
                "product_name": row["product_name"],
                "units_sold": row["units_sold"] or 0,
                "order_count": row["order_count"],
                "revenue": _money(row["revenue"]),
            }
        )

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "results": results,
    }


def get_store_performance(
    *,
    user,
    start_date=None,
    end_date=None,
    store_id=None,
):
    (
        orders,
        start_date,
        end_date,
        _,
        _,
    ) = get_scoped_orders(
        user=user,
        start_date=start_date,
        end_date=end_date,
        store_id=store_id,
    )

    rows = (
        orders.values(
            "store_id",
            "store__name",
        )
        .annotate(
            total_orders=Count("id"),
            paid_orders=Count(
                "id",
                filter=Q(payment_status=(Order.PaymentStatus.PAID)),
            ),
            delivered_orders=Count(
                "id",
                filter=Q(
                    status=Order.Status.DELIVERED,
                ),
            ),
            cancelled_orders=Count(
                "id",
                filter=Q(
                    status=Order.Status.CANCELLED,
                ),
            ),
            revenue=Sum(
                "total",
                filter=Q(payment_status=(Order.PaymentStatus.PAID)),
            ),
        )
        .order_by("-revenue")
    )

    results = []

    for row in rows:
        results.append(
            {
                "store_id": str(row["store_id"]),
                "store_name": (row["store__name"]),
                "total_orders": (row["total_orders"]),
                "paid_orders": (row["paid_orders"]),
                "delivered_orders": (row["delivered_orders"]),
                "cancelled_orders": (row["cancelled_orders"]),
                "revenue": _money(row["revenue"]),
            }
        )

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "results": results,
    }


def get_low_stock_queryset(
    *,
    user,
    store_id=None,
):
    _ensure_store_access(
        user=user,
        store_id=store_id,
    )

    available_quantity_expression = ExpressionWrapper(
        F("quantity") - F("reserved_quantity"),
        output_field=IntegerField(),
    )

    queryset = (
        StoreInventory.objects.select_related(
            "store",
            "product",
        )
        .annotate(calculated_available_quantity=(available_quantity_expression))
        .filter(
            is_available=True,
            calculated_available_quantity__lte=F("low_stock_threshold"),
        )
    )

    if store_id is not None:
        queryset = queryset.filter(
            store_id=store_id,
        )

    elif not is_platform_admin(user):
        managed_store_ids = get_managed_store_ids(user)

        queryset = queryset.filter(
            store_id__in=managed_store_ids,
        )

    return queryset.order_by(
        "calculated_available_quantity",
        "product__name",
    )


def get_low_stock_data(
    *,
    user,
    store_id=None,
):
    queryset = get_low_stock_queryset(
        user=user,
        store_id=store_id,
    )

    results = []

    for inventory in queryset[:100]:
        results.append(
            {
                "inventory_id": str(inventory.id),
                "store_id": str(inventory.store_id),
                "store_name": (inventory.store.name),
                "product_id": str(inventory.product_id),
                "product_name": (inventory.product.name),
                "quantity": inventory.quantity,
                "reserved_quantity": (inventory.reserved_quantity),
                "available_quantity": (inventory.calculated_available_quantity),
                "low_stock_threshold": (inventory.low_stock_threshold),
            }
        )

    return {
        "count": queryset.count(),
        "results": results,
    }


def get_delivery_performance(
    *,
    user,
    start_date=None,
    end_date=None,
    store_id=None,
):
    (
        orders,
        start_date,
        end_date,
        _,
        _,
    ) = get_scoped_orders(
        user=user,
        start_date=start_date,
        end_date=end_date,
        store_id=store_id,
    )

    deliveries = Delivery.objects.filter(
        order__in=orders,
    )

    status_breakdown = list(
        deliveries.values("status")
        .annotate(
            count=Count("id"),
        )
        .order_by("status")
    )

    completed_deliveries = deliveries.filter(
        status=Delivery.Status.DELIVERED,
        assigned_at__isnull=False,
        delivered_at__isnull=False,
    ).annotate(
        delivery_duration=ExpressionWrapper(
            F("delivered_at") - F("assigned_at"),
            output_field=DurationField(),
        )
    )

    average_duration = completed_deliveries.aggregate(
        average=Avg("delivery_duration"),
    )["average"]

    average_minutes = None

    if average_duration is not None:
        average_minutes = round(
            average_duration.total_seconds() / 60,
            2,
        )

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "total_deliveries": deliveries.count(),
        "delivered": deliveries.filter(
            status=Delivery.Status.DELIVERED,
        ).count(),
        "average_assigned_to_delivered_minutes": (average_minutes),
        "status_breakdown": status_breakdown,
    }
