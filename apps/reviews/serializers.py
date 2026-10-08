from rest_framework import serializers

from apps.catalog.models import Product

from .models import Review
from .services import (
    get_product_rating_summary,
    has_verified_purchase,
)


class ReviewSerializer(serializers.ModelSerializer):
    customer_id = serializers.CharField(
        source="user.customer_id",
        read_only=True,
    )

    customer_name = serializers.SerializerMethodField()

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    class Meta:
        model = Review

        fields = (
            "id",
            "product",
            "product_name",
            "customer_id",
            "customer_name",
            "rating",
            "comment",
            "is_verified_purchase",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "product_name",
            "customer_id",
            "customer_name",
            "is_verified_purchase",
            "created_at",
            "updated_at",
        )

    def get_customer_name(self, obj):
        full_name = obj.user.get_full_name().strip()

        if full_name:
            return full_name

        return "Bokku Customer"

    def validate_product(self, product):
        request = self.context["request"]

        if self.instance and self.instance.product_id != product.id:
            raise serializers.ValidationError(
                "The product on an existing review cannot be changed."
            )

        if not self.instance:
            if Review.objects.filter(
                user=request.user,
                product=product,
            ).exists():
                raise serializers.ValidationError(
                    "You have already reviewed this product."
                )

            if not has_verified_purchase(
                user=request.user,
                product=product,
            ):
                raise serializers.ValidationError(
                    "You can only review products from a paid, " "delivered order."
                )

        return product

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")

        return value

    def validate_comment(self, value):
        return value.strip()


class ProductRatingSummarySerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    average_rating = serializers.FloatField()
    review_count = serializers.IntegerField()


class ReviewEligibilitySerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    eligible = serializers.BooleanField()
    already_reviewed = serializers.BooleanField()
