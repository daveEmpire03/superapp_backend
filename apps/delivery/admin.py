from django.contrib import admin

from .models import (
    Delivery,
    DeliveryStatusHistory,
)


class DeliveryStatusHistoryInline(admin.TabularInline):
    model = DeliveryStatusHistory
    extra = 0

    fields = (
        "status",
        "changed_by",
        "note",
        "created_at",
    )

    readonly_fields = fields

    can_delete = False

    def has_add_permission(
        self,
        request,
        obj=None,
    ):
        return False


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "rider",
        "status",
        "assigned_at",
        "accepted_at",
        "picked_up_at",
        "out_for_delivery_at",
        "delivered_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "order__reference",
        "order__user__email",
        "rider__username",
        "rider__email",
        "rider__phone",
    )

    autocomplete_fields = (
        "order",
        "rider",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)

    inlines = [
        DeliveryStatusHistoryInline,
    ]


@admin.register(DeliveryStatusHistory)
class DeliveryStatusHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "delivery",
        "status",
        "changed_by",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "delivery__order__reference",
        "changed_by__email",
        "note",
    )

    autocomplete_fields = (
        "delivery",
        "changed_by",
    )

    readonly_fields = (
        "id",
        "delivery",
        "status",
        "changed_by",
        "note",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)

    def has_add_permission(
        self,
        request,
    ):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False
