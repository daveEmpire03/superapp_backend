from django.contrib import admin

from .models import (
    DeviceToken,
    Notification,
)


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "platform",
        "is_active",
        "updated_at",
    )

    list_filter = (
        "platform",
        "is_active",
    )

    search_fields = (
        "user__email",
        "user__username",
        "token",
    )

    autocomplete_fields = ("user",)

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "notification_type",
        "title",
        "is_read",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "is_read",
        "created_at",
    )

    search_fields = (
        "user__email",
        "user__username",
        "title",
        "message",
    )

    autocomplete_fields = ("user",)

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )
