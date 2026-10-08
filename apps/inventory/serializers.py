from rest_framework import serializers

from apps.catalog.models import Product
from apps.stores.models import Store

from .models import StoreInventory


class StoreInventorySerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(
        source="store.name",
        read_only=True,
    )

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    product_image = serializers.ImageField(
        source="product.image",
        read_only=True,
    )

    product_sku = serializers.CharField(
        source="product.sku",
        read_only=True,
    )

    product_brand = serializers.CharField(
        source="product.brand",
        read_only=True,
    )

    available_quantity = serializers.IntegerField(
        read_only=True,
    )

    is_in_stock = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = StoreInventory

        fields = (
            "id",
            "store",
            "store_name",
            "product",
            "product_name",
            "product_image",
            "product_sku",
            "product_brand",
            "price",
            "compare_at_price",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "is_available",
            "is_in_stock",
            "low_stock_threshold",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "store",
            "product",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "is_in_stock",
            "created_at",
            "updated_at",
        )


class InventoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreInventory

        fields = (
            "store",
            "product",
            "price",
            "compare_at_price",
            "quantity",
            "low_stock_threshold",
            "is_available",
        )

    def validate_store(self, store):
        if not store.is_active:
            raise serializers.ValidationError(
                "Inventory cannot be created " "for an inactive store."
            )

        return store

    def validate_product(self, product):
        if not product.is_active:
            raise serializers.ValidationError(
                "Inventory cannot be created " "for an inactive product."
            )

        return product

    def validate(self, attrs):
        store = attrs.get("store")
        product = attrs.get("product")

        if (
            store
            and product
            and StoreInventory.objects.filter(
                store=store,
                product=product,
            ).exists()
        ):
            raise serializers.ValidationError(
                {"product": ("This product already has " "inventory for this store.")}
            )

        compare_at_price = attrs.get("compare_at_price")

        price = attrs.get("price")

        if (
            compare_at_price is not None
            and price is not None
            and compare_at_price < price
        ):
            raise serializers.ValidationError(
                {
                    "compare_at_price": (
                        "Compare-at price cannot be " "lower than the selling price."
                    )
                }
            )

        return attrs


class InventoryUpdateSerializer(serializers.Serializer):
    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
    )

    compare_at_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )

    low_stock_threshold = serializers.IntegerField(
        min_value=0,
        required=False,
    )

    is_available = serializers.BooleanField(
        required=False,
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "At least one inventory field " "must be provided."
            )

        instance = self.context.get("inventory")

        if instance:
            price = attrs.get(
                "price",
                instance.price,
            )

            compare_at_price = attrs.get(
                "compare_at_price",
                instance.compare_at_price,
            )

            if compare_at_price is not None and compare_at_price < price:
                raise serializers.ValidationError(
                    {
                        "compare_at_price": (
                            "Compare-at price cannot "
                            "be lower than the "
                            "selling price."
                        )
                    }
                )

        return attrs


class InventoryStockAdjustmentSerializer(serializers.Serializer):
    quantity = serializers.IntegerField()

    reason = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )

    def validate_quantity(self, value):
        if value == 0:
            raise serializers.ValidationError("Stock adjustment cannot be zero.")

        return value
