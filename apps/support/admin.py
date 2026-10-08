from django.contrib import admin

from .models import (
    SupportMessage,
    SupportStatusHistory,
    SupportTicket,
)


class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 0

    fields = (
        "author",
        "is_staff_reply",
        "message",
        "created_at",
    )

    readonly_fields = (
        "author",
        "is_staff_reply",
        "message",
        "created_at",
    )

    can_delete = False


class SupportStatusHistoryInline(admin.TabularInline):
    model = SupportStatusHistory
    extra = 0

    fields = (
        "from_status",
        "to_status",
        "changed_by",
        "note",
        "created_at",
    )

    readonly_fields = fields

    can_delete = False


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "user",
        "category",
        "priority",
        "status",
        "store",
        "assigned_to",
        "created_at",
    )

    list_filter = (
        "status",
        "priority",
        "category",
        "store",
        "created_at",
    )

    search_fields = (
        "subject",
        "message",
        "user__email",
        "user__customer_id",
        "order__reference",
    )

    autocomplete_fields = (
        "user",
        "order",
        "store",
        "assigned_to",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("-updated_at",)

    inlines = (
        SupportMessageInline,
        SupportStatusHistoryInline,
    )


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = (
        "ticket",
        "author",
        "is_staff_reply",
        "created_at",
    )

    list_filter = (
        "is_staff_reply",
        "created_at",
    )

    search_fields = (
        "ticket__subject",
        "message",
        "author__email",
    )

    autocomplete_fields = (
        "ticket",
        "author",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


@admin.register(SupportStatusHistory)
class SupportStatusHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "ticket",
        "from_status",
        "to_status",
        "changed_by",
        "created_at",
    )

    list_filter = (
        "to_status",
        "created_at",
    )

    search_fields = (
        "ticket__subject",
        "note",
        "changed_by__email",
    )

    autocomplete_fields = (
        "ticket",
        "changed_by",
    )

    readonly_fields = (
        "id",
        "ticket",
        "from_status",
        "to_status",
        "changed_by",
        "note",
        "created_at",
        "updated_at",
    )
