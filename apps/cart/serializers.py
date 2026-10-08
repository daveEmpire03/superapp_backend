from decimal import Decimal

from rest_framework import serializers

from apps.inventory.models import StoreInventory

from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(
        source="inventory.product.id",
        read_only=True,
    )
    product_name = serializers.CharField(
        source="inventory.product.name",
        read_only=True,
    )
    product_image = serializers.ImageField(
        source="inventory.product.image",
        read_only=True,
    )
    sku = serializers.CharField(
        source="inventory.product.sku",
        read_only=True,
    )
    unit_price = serializers.DecimalField(
        source="inventory.price",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    available_quantity = serializers.IntegerField(
        source="inventory.quantity",
        read_only=True,
    )
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = (
            "id",
            "inventory",
            "product_id",
            "product_name",
            "product_image",
            "sku",
            "quantity",
            "unit_price",
            "available_quantity",
            "line_total",
        )
        read_only_fields = fields

    def get_line_total(self, obj):
        return obj.inventory.price * obj.quantity


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(
        many=True,
        read_only=True,
    )

    store_name = serializers.CharField(
        source="store.name",
        read_only=True,
    )

    subtotal = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = (
            "id",
            "store",
            "store_name",
            "items",
            "item_count",
            "subtotal",
            "created_at",
            "updated_at",
        )

        read_only_fields = fields

    def get_subtotal(self, obj):
        return sum(
            (item.inventory.price * item.quantity for item in obj.items.all()),
            Decimal("0.00"),
        )

    def get_item_count(self, obj):
        return sum(item.quantity for item in obj.items.all())


class AddCartItemSerializer(serializers.Serializer):
    inventory_id = serializers.UUIDField()
    quantity = serializers.IntegerField(
        min_value=1,
        default=1,
    )

    def validate(self, attrs):
        inventory_id = attrs["inventory_id"]
        quantity = attrs["quantity"]

        try:
            inventory = StoreInventory.objects.select_related(
                "store",
                "product",
            ).get(
                id=inventory_id,
                is_available=True,
                store__is_active=True,
                product__is_active=True,
            )

        except StoreInventory.DoesNotExist:
            raise serializers.ValidationError(
                {"inventory_id": "This product is not available."}
            )

        if inventory.quantity <= 0:
            raise serializers.ValidationError(
                {"inventory_id": "This product is out of stock."}
            )

        if quantity > inventory.quantity:
            raise serializers.ValidationError(
                {
                    "quantity": (
                        "Requested quantity exceeds "
                        f"available stock ({inventory.quantity})."
                    )
                }
            )

        attrs["inventory"] = inventory

        return attrs


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(
        min_value=1,
    )

    def validate_quantity(self, quantity):
        cart_item = self.context["cart_item"]

        available_quantity = cart_item.inventory.quantity

        if quantity > available_quantity:
            raise serializers.ValidationError(
                (
                    "Requested quantity exceeds "
                    f"available stock ({available_quantity})."
                )
            )

        return quantity
