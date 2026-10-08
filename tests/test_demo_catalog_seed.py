from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.catalog.models import Category, Product
from apps.inventory.models import InventoryMovement, StoreInventory
from apps.stores.models import Store


class DemoCatalogSeedTests(TestCase):
    def setUp(self):
        self.store = Store.objects.create(
            name="Test Supermarket",
            code="demo-store",
            address="1 Main Road",
            city="Ibadan",
            state="Oyo",
            is_active=True,
        )

    def test_seeding_is_repeatable_and_preserves_existing_inventory(self):
        output = StringIO()
        call_command(
            "seed_demo_catalog",
            store_code=self.store.code,
            quantity=10,
            stdout=output,
        )
        self.assertEqual(Category.objects.count(), 10)
        self.assertEqual(Product.objects.filter(sku__startswith="BKM-DEMO-").count(), 58)
        self.assertEqual(StoreInventory.objects.filter(store=self.store).count(), 58)
        self.assertEqual(InventoryMovement.objects.count(), 58)

        inventory = StoreInventory.objects.filter(store=self.store).first()
        inventory.price = 999
        inventory.quantity = 7
        inventory.save(update_fields=["price", "quantity"])

        call_command(
            "seed_demo_catalog",
            store_code=self.store.code,
            quantity=100,
            stdout=output,
        )
        self.assertEqual(Product.objects.filter(sku__startswith="BKM-DEMO-").count(), 58)
        self.assertEqual(StoreInventory.objects.filter(store=self.store).count(), 58)
        self.assertEqual(InventoryMovement.objects.count(), 58)
        inventory.refresh_from_db()
        self.assertEqual(inventory.price, 999)
        self.assertEqual(inventory.quantity, 7)

    def test_catalog_only_option_does_not_create_inventory(self):
        call_command("seed_demo_catalog", stdout=StringIO())
        self.assertEqual(Product.objects.filter(sku__startswith="BKM-DEMO-").count(), 58)
        self.assertFalse(StoreInventory.objects.exists())
