from rest_framework import serializers

from .models import (
    Order,
    OrderItem,
    OrderStatusHistory,
)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem

        fields = (
            "id",
            "product",
            "product_name",
            "sku",
            "unit_price",
            "quantity",
            "line_total",
        )


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory

        fields = (
            "id",
            "status",
            "note",
            "created_at",
        )


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(
        many=True,
        read_only=True,
    )

    status_history = OrderStatusHistorySerializer(
        many=True,
        read_only=True,
    )

    store_name = serializers.CharField(
        source="store.name",
        read_only=True,
    )

    class Meta:
        model = Order

        fields = (
            "id",
            "reference",
            "store",
            "store_name",
            "fulfilment_type",
            "status",
            "payment_status",
            "subtotal",
            "discount",
            "delivery_fee",
            "total",
            "promotion_code",
            "delivery_address_snapshot",
            "notes",
            "reservation_expires_at",
            "items",
            "status_history",
            "created_at",
            "updated_at",
        )

        read_only_fields = fields


class CheckoutSerializer(serializers.Serializer):
    fulfilment_type = serializers.ChoiceField(
        choices=Order.Fulfilment.choices,
    )

    delivery_address = serializers.JSONField(
        required=False,
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
    )

    promotion_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        trim_whitespace=True,
    )

    def validate_promotion_code(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        fulfilment_type = attrs["fulfilment_type"]

        if fulfilment_type == Order.Fulfilment.DELIVERY and not attrs.get(
            "delivery_address"
        ):
            raise serializers.ValidationError(
                {"delivery_address": "Delivery address is required."}
            )

        return attrs
