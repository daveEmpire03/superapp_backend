from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.cart.models import Cart, CartItem
from apps.catalog.models import Category, Product
from apps.inventory.models import StoreInventory
from apps.stores.models import Store


class CartReservedStockTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="stock-check@example.com",
            password="StrongTestPassword123!",
            is_email_verified=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.store = Store.objects.create(
            name="Test Store",
            code="stock-test",
            address="Main Road",
            city="Ibadan",
            state="Oyo",
        )
        self.category = Category.objects.create(name="Groceries", slug="groceries")
        self.product = Product.objects.create(
            category=self.category,
            name="Rice",
            slug="rice",
            sku="RICE-001",
        )
        self.inventory = StoreInventory.objects.create(
            store=self.store,
            product=self.product,
            price=Decimal("1200.00"),
            quantity=10,
            reserved_quantity=7,
        )

    def test_add_rejects_reserved_stock(self):
        response = self.client.post(
            "/api/v1/cart/items/",
            {"inventory_id": str(self.inventory.id), "quantity": 4},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CartItem.objects.filter(cart__user=self.user).exists())

    def test_add_allows_only_unreserved_stock(self):
        response = self.client.post(
            "/api/v1/cart/items/",
            {"inventory_id": str(self.inventory.id), "quantity": 3},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            CartItem.objects.get(cart__user=self.user).quantity, 3
        )

    def test_update_rejects_reserved_stock(self):
        cart = Cart.objects.create(user=self.user, store=self.store)
        item = CartItem.objects.create(
            cart=cart, inventory=self.inventory, quantity=2
        )
        response = self.client.patch(
            f"/api/v1/cart/items/{item.id}/",
            {"quantity": 4},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)

    def test_cart_exposes_unreserved_quantity(self):
        cart = Cart.objects.create(user=self.user, store=self.store)
        CartItem.objects.create(cart=cart, inventory=self.inventory, quantity=2)
        response = self.client.get("/api/v1/cart/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["items"][0]["available_quantity"], 3)
