from django.contrib import admin

from .models import ParcelShipment, ParcelStatusHistory


class ParcelStatusHistoryInline(admin.TabularInline):
    model = ParcelStatusHistory
    extra = 0
    can_delete = False
    readonly_fields = ("status", "changed_by", "note", "created_at")


@admin.register(ParcelShipment)
class ParcelShipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "sender", "driver", "package_size", "status", "quoted_fare", "payment_method", "payment_status", "created_at")
    list_filter = ("status", "package_size", "payment_method", "payment_status")
    search_fields = ("id", "sender__email", "driver__email", "recipient_name", "recipient_phone")
    readonly_fields = ("id", "requested_at", "assigned_at", "picked_up_at", "in_transit_at", "delivered_at", "cancelled_at", "created_at", "updated_at")
    inlines = (ParcelStatusHistoryInline,)
