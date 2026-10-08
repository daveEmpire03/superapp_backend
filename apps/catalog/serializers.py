from decimal import Decimal

from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    image_url = serializers.ImageField(
        source="image",
        read_only=True,
        allow_null=True,
    )
    item_count = serializers.IntegerField(
        read_only=True,
    )

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "image_url",
            "item_count",
            "sort_order",
        )


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.UUIDField(
        source="category_id",
        read_only=True,
    )

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    category_slug = serializers.CharField(
        source="category.slug",
        read_only=True,
    )

    image_url = serializers.ImageField(
        source="image",
        read_only=True,
        allow_null=True,
    )

    store_id = serializers.SerializerMethodField()
    inventory_id = serializers.SerializerMethodField()

    price = serializers.SerializerMethodField()
    compare_at_price = serializers.SerializerMethodField()
    old_price = serializers.SerializerMethodField()

    available_quantity = serializers.SerializerMethodField()
    stock_count = serializers.SerializerMethodField()

    is_available = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()

    is_deal = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    badge = serializers.SerializerMethodField()

    details = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "category",
            "category_name",
            "category_slug",
            "name",
            "slug",
            "brand",
            "sku",
            "size",
            "description",
            "image_url",
            "store_id",
            "inventory_id",
            "price",
            "compare_at_price",
            "old_price",
            "available_quantity",
            "stock_count",
            "is_available",
            "in_stock",
            "is_deal",
            "discount_amount",
            "discount_percentage",
            "badge",
            "details",
            "created_at",
            "updated_at",
        )

    def _inventory(self, obj):
        inventories = getattr(
            obj,
            "_selected_store_inventory",
            None,
        )

        if inventories:
            return inventories[0]

        return None

    def get_store_id(self, obj):
        inventory = self._inventory(obj)

        if inventory is None:
            return None

        return str(inventory.store_id)

    def get_inventory_id(self, obj):
        inventory = self._inventory(obj)

        if inventory is None:
            return None

        return str(inventory.id)

    def get_price(self, obj):
        inventory = self._inventory(obj)

        if inventory is None:
            return None

        return str(inventory.price)

    def get_compare_at_price(self, obj):
        inventory = self._inventory(obj)

        if inventory is None:
            return None

        if inventory.compare_at_price is None:
            return None

        return str(inventory.compare_at_price)

    def get_old_price(self, obj):
        return self.get_compare_at_price(obj)

    def get_available_quantity(self, obj):
        inventory = self._inventory(obj)

        if inventory is None:
            return 0

        return inventory.available_quantity

    def get_stock_count(self, obj):
        return self.get_available_quantity(obj)

    def get_is_available(self, obj):
        inventory = self._inventory(obj)

        if inventory is None:
            return False

        return inventory.is_available

    def get_in_stock(self, obj):
        inventory = self._inventory(obj)

        if inventory is None:
            return False

        return inventory.is_in_stock

    def get_is_deal(self, obj):
        inventory = self._inventory(obj)

        if inventory is None:
            return False

        compare_at_price = inventory.compare_at_price

        if compare_at_price is None:
            return False

        return compare_at_price > inventory.price

    def _discount_amount(self, obj):
        inventory = self._inventory(obj)

        if inventory is None:
            return None

        compare_at_price = inventory.compare_at_price

        if compare_at_price is None or compare_at_price <= inventory.price:
            return None

        return compare_at_price - inventory.price

    def get_discount_amount(self, obj):
        discount = self._discount_amount(obj)

        if discount is None:
            return None

        return str(discount)

    def get_discount_percentage(self, obj):
        inventory = self._inventory(obj)

        if inventory is None:
            return None

        compare_at_price = inventory.compare_at_price

        if (
            compare_at_price is None
            or compare_at_price <= inventory.price
            or compare_at_price == Decimal("0")
        ):
            return None

        discount = compare_at_price - inventory.price

        percentage = (discount / compare_at_price) * Decimal("100")

        return int(round(percentage))

    def get_badge(self, obj):
        discount = self._discount_amount(obj)

        if discount is None:
            return None

        return f"Save ₦{discount:,.0f}"

    def get_details(self, obj):
        details = {
            "SKU": obj.sku,
            "Category": obj.category.name,
        }

        if obj.brand:
            details["Brand"] = obj.brand

        if obj.size:
            details["Size"] = obj.size

        return details
