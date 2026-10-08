from rest_framework import serializers

from .models import LoyaltyEntry


class LoyaltyEntrySerializer(serializers.ModelSerializer):
    order_reference = serializers.CharField(
        source="order.reference",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = LoyaltyEntry

        fields = (
            "id",
            "entry_type",
            "points",
            "reason",
            "reference",
            "order",
            "order_reference",
            "created_at",
        )

        read_only_fields = fields
