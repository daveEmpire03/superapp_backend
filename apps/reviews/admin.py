from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "user",
        "rating",
        "is_verified_purchase",
        "is_approved",
        "created_at",
    )

    list_filter = (
        "rating",
        "is_verified_purchase",
        "is_approved",
        "created_at",
    )

    search_fields = (
        "product__name",
        "user__customer_id",
        "user__email",
        "comment",
    )

    autocomplete_fields = (
        "product",
        "user",
    )

    readonly_fields = (
        "id",
        "is_verified_purchase",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)
