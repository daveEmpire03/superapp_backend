from django.contrib import admin

from .models import Store, StoreStaffMembership


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "city",
        "state",
        "is_active",
        "supports_delivery",
        "supports_pickup",
        "opens_at",
        "closes_at",
    )

    list_filter = (
        "is_active",
        "supports_delivery",
        "supports_pickup",
        "state",
        "city",
    )

    search_fields = (
        "name",
        "code",
        "address",
        "city",
        "state",
        "phone",
    )

    prepopulated_fields = {
        "code": ("name",),
    }

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


@admin.register(StoreStaffMembership)
class StoreStaffMembershipAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "store",
        "role",
        "is_active",
        "created_at",
    )

    list_filter = (
        "role",
        "is_active",
        "store",
    )

    search_fields = (
        "user__username",
        "user__email",
        "store__name",
        "store__code",
    )

    autocomplete_fields = (
        "user",
        "store",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )
