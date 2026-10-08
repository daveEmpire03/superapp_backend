from django.contrib import admin

from .models import AnalyticsEvent


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "created_at",
    )

    list_filter = (
        "name",
        "created_at",
    )

    search_fields = (
        "name",
        "user__email",
        "user__customer_id",
    )

    autocomplete_fields = ("user",)

    readonly_fields = (
        "id",
        "user",
        "name",
        "properties",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)
