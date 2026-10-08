from django.contrib import admin
from .models import Order, OrderItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "sku", "unit_price", "line_total")


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "user",
        "store",
        "fulfilment_type",
        "status",
        "payment_status",
        "total",
        "created_at",
    )
    list_filter = (
        "status",
        "payment_status",
        "fulfilment_type",
        "store",
    )
    search_fields = (
        "reference",
        "user__username",
        "user__email",
        "user__phone",
    )
    autocomplete_fields = ("user", "store")
    readonly_fields = (
        "id",
        "reference",
        "created_at",
        "updated_at",
    )
    inlines = (OrderItemInline, OrderStatusHistoryInline)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "product_name",
        "order",
        "sku",
        "unit_price",
        "quantity",
        "line_total",
    )
    search_fields = ("product_name", "sku", "order__reference")
    autocomplete_fields = ("order", "product")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("order", "status", "note", "created_at")
    list_filter = ("status",)
    search_fields = ("order__reference", "note")
    autocomplete_fields = ("order",)
    readonly_fields = ("id", "created_at", "updated_at")
