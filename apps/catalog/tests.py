from django.test import TestCase

from apps.catalog.models import Category, Product


class ProductSkuGenerationTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Rice and Grains",
            slug="rice-and-grains",
        )

    def create_product(self, *, slug, sku="", **overrides):
        values = {
            "category": self.category,
            "name": "Rice",
            "brand": "Big Bull",
            "size": "5 kg",
            "slug": slug,
            "sku": sku,
        }
        values.update(overrides)
        product = Product(**values)
        product.save()
        return product

    def test_generates_readable_sku_when_blank(self):
        product = self.create_product(slug="big-bull-rice")

        self.assertEqual(product.sku, "BIG-BULL-RICE-5-KG")

    def test_adds_suffix_when_generated_sku_already_exists(self):
        first = self.create_product(slug="big-bull-rice")
        second = self.create_product(slug="big-bull-rice-second")

        self.assertEqual(first.sku, "BIG-BULL-RICE-5-KG")
        self.assertEqual(second.sku, "BIG-BULL-RICE-5-KG-2")

    def test_preserves_a_manually_supplied_sku(self):
        product = self.create_product(
            slug="custom-sku-rice",
            sku="BOKKU-RICE-001",
        )

        self.assertEqual(product.sku, "BOKKU-RICE-001")

    def test_generates_sku_when_blank_and_update_fields_is_used(self):
        product = self.create_product(slug="update-fields-rice")
        product.sku = ""
        product.name = "Premium Rice"
        product.save(update_fields={"name"})

        product.refresh_from_db()
        self.assertEqual(product.sku, "BIG-BULL-PREMIUM-RICE-5-KG")
