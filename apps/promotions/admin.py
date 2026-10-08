from django.contrib import admin

from .models import (
    Promotion,
    PromotionRedemption,
)


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "store",
        "discount_type",
        "value",
        "min_order_amount",
        "max_discount_amount",
        "starts_at",
        "ends_at",
        "usage_limit",
        "per_user_limit",
        "is_active",
    )

    list_filter = (
        "discount_type",
        "is_active",
        "store",
    )

    search_fields = (
        "code",
        "title",
        "store__name",
    )

    autocomplete_fields = ("store",)

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)


@admin.register(PromotionRedemption)
class PromotionRedemptionAdmin(admin.ModelAdmin):
    list_display = (
        "promotion",
        "user",
        "order",
        "discount_amount",
        "created_at",
    )

    list_filter = (
        "promotion",
        "created_at",
    )

    search_fields = (
        "promotion__code",
        "user__email",
        "order__reference",
    )

    autocomplete_fields = (
        "promotion",
        "user",
        "order",
    )

    readonly_fields = (
        "id",
        "promotion",
        "user",
        "order",
        "discount_amount",
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
