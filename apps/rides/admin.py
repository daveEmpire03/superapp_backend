from django.contrib import admin

from .models import Ride, RideDriverProfile, RideStatusHistory


class RideStatusHistoryInline(admin.TabularInline):
    model = RideStatusHistory
    extra = 0
    can_delete = False
    readonly_fields = ("status", "changed_by", "note", "created_at")


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "passenger",
        "driver",
        "vehicle_type",
        "status",
        "quoted_fare",
        "payment_method",
        "payment_status",
        "created_at",
    )
    list_filter = ("status", "vehicle_type", "payment_method", "payment_status")
    search_fields = ("id", "passenger__email", "driver__email", "pickup_address", "destination_address")
    readonly_fields = (
        "id", "requested_at", "driver_assigned_at", "trip_started_at",
        "trip_completed_at", "cancelled_at", "created_at", "updated_at",
    )
    inlines = (RideStatusHistoryInline,)


@admin.register(RideDriverProfile)
class RideDriverProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user", "vehicle_type", "vehicle_plate", "is_approved",
        "is_suspended", "is_available", "last_location_at",
    )
    list_filter = ("vehicle_type", "is_approved", "is_suspended", "is_available")
    search_fields = ("user__email", "vehicle_plate", "vehicle_make")
    readonly_fields = ("created_at", "updated_at", "last_location_at")
    actions = ("approve_drivers", "suspend_drivers", "unsuspend_drivers")

    @admin.action(description="Approve selected drivers")
    def approve_drivers(self, request, queryset):
        queryset.update(is_approved=True, is_suspended=False, is_available=False)

    @admin.action(description="Suspend selected drivers")
    def suspend_drivers(self, request, queryset):
        queryset.update(is_suspended=True, is_available=False)

    @admin.action(description="Remove suspension from selected drivers")
    def unsuspend_drivers(self, request, queryset):
        queryset.update(is_suspended=False, is_available=False)
