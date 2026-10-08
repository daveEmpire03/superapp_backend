from django.contrib import admin

from .models import StoreInventory


@admin.register(StoreInventory)
class StoreInventoryAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "store",
        "price",
        "compare_at_price",
        "quantity",
        "low_stock_threshold",
        "is_available",
        "updated_at",
    )

    list_filter = (
        "store",
        "is_available",
    )

    search_fields = (
        "product__name",
        "product__sku",
        "product__brand",
        "store__name",
    )

    autocomplete_fields = (
        "store",
        "product",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = (
        "store",
        "product__name",
    )
