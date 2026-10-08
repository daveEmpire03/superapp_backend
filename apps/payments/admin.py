from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "tx_ref",
        "order",
        "provider",
        "amount",
        "currency",
        "status",
        "provider_transaction_id",
        "created_at",
    )
    list_filter = ("provider", "status", "currency")
    search_fields = (
        "tx_ref",
        "provider_transaction_id",
        "order__reference",
        "order__user__email",
    )
    autocomplete_fields = ("order",)
    readonly_fields = (
        "id",
        "raw_response",
        "created_at",
        "updated_at",
    )
