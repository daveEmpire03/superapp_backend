from rest_framework import serializers

from .models import Promotion


class PromotionSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(
        source="store.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Promotion

        fields = [
            "id",
            "code",
            "title",
            "description",
            "store",
            "store_name",
            "discount_type",
            "value",
            "min_order_amount",
            "max_discount_amount",
            "starts_at",
            "ends_at",
            "usage_limit",
            "per_user_limit",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_code(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        starts_at = attrs.get(
            "starts_at",
            getattr(
                self.instance,
                "starts_at",
                None,
            ),
        )

        ends_at = attrs.get(
            "ends_at",
            getattr(
                self.instance,
                "ends_at",
                None,
            ),
        )

        discount_type = attrs.get(
            "discount_type",
            getattr(
                self.instance,
                "discount_type",
                None,
            ),
        )

        value = attrs.get(
            "value",
            getattr(
                self.instance,
                "value",
                None,
            ),
        )

        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError(
                {"ends_at": "End time must be after " "start time."}
            )

        if (
            discount_type == Promotion.DiscountType.PERCENT
            and value is not None
            and value > 100
        ):
            raise serializers.ValidationError(
                {"value": "Percentage discount cannot " "exceed 100."}
            )

        return attrs


class PromotionValidationSerializer(serializers.Serializer):
    code = serializers.CharField(
        max_length=50,
        trim_whitespace=True,
    )

    store_id = serializers.UUIDField()

    subtotal = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
    )

    def validate_code(self, value):
        return value.strip().upper()
