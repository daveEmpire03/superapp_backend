from django.contrib import admin

from .models import LoyaltyEntry


@admin.register(LoyaltyEntry)
class LoyaltyEntryAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "entry_type",
        "points",
        "order",
        "reason",
        "reference",
        "created_at",
    )

    list_filter = (
        "entry_type",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "reason",
        "reference",
        "order__reference",
    )

    autocomplete_fields = (
        "user",
        "order",
        "created_by",
    )

    readonly_fields = (
        "id",
        "user",
        "order",
        "entry_type",
        "points",
        "reason",
        "reference",
        "created_by",
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
