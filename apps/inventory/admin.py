from django.contrib import admin
from django.db.models import F

from unfold.admin import ModelAdmin

from .models import InventoryMovement, StoreInventory


class StockHealthFilter(admin.SimpleListFilter):
    title = "Stock health"
    parameter_name = "stock_health"

    def lookups(self, request, model_admin):
        return (("low", "Low stock"), ("healthy", "Healthy stock"))

    def queryset(self, request, queryset):
        queryset = queryset.annotate(
            _available_quantity=F("quantity") - F("reserved_quantity")
        )
        if self.value() == "low":
            return queryset.filter(_available_quantity__lte=F("low_stock_threshold"))
        if self.value() == "healthy":
            return queryset.filter(_available_quantity__gt=F("low_stock_threshold"))
        return queryset


@admin.register(StoreInventory)
class StoreInventoryAdmin(ModelAdmin):
    list_display = (
        "product", "store", "price", "quantity", "available_quantity",
        "low_stock_threshold", "is_available", "updated_at",
    )
    list_filter = (StockHealthFilter, "store", "is_available")
    search_fields = (
        "product__name", "product__sku", "product__brand", "store__name",
    )
    autocomplete_fields = ("store", "product")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("store", "product__name")
    list_select_related = ("store", "product")
    list_per_page = 25

    @admin.display(description="Available stock")
    def available_quantity(self, obj):
        return obj.available_quantity


@admin.register(InventoryMovement)
class InventoryMovementAdmin(ModelAdmin):
    list_display = (
        "inventory", "movement_type", "quantity_change",
        "quantity_before", "quantity_after", "reserved_before",
        "reserved_after", "performed_by", "created_at",
    )
    list_filter = ("movement_type", "created_at")
    search_fields = (
        "inventory__product__name", "inventory__product__sku",
        "inventory__store__name", "reference", "reason",
    )
    list_select_related = (
        "inventory", "inventory__product", "inventory__store", "performed_by",
    )
    readonly_fields = (
        "id", "inventory", "movement_type", "quantity_change",
        "quantity_before", "quantity_after", "reserved_before",
        "reserved_after", "reason", "performed_by", "reference",
        "created_at", "updated_at",
    )
    ordering = ("-created_at",)
    list_per_page = 30

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
