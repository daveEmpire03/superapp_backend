"""Populate a safe, repeatable demo catalog; prices are examples, not live quotes."""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.catalog.models import Category, Product
from apps.inventory.models import InventoryMovement, StoreInventory
from apps.stores.models import Store


CATEGORIES = [["Rice, Grains & Pasta",1], ["Cooking Essentials",2], ["Breakfast & Cereals",3], ["Milk & Dairy",4], ["Beverages & Water",5], ["Snacks & Biscuits",6], ["Personal Care",7], ["Home & Cleaning",8], ["Canned & Packaged Food",9], ["Fresh Produce",10]]
PRODUCTS = [[0,"0101","Golden Penny Spaghetti","Golden Penny","500g",1100],[0,"0102","Golden Penny Macaroni","Golden Penny","500g",1150],[0,"0103","Parboiled Rice","Bokku Essentials","5kg",12500],[0,"0104","Local Ofada Rice","Bokku Essentials","2kg",6100],[0,"0105","Semolina","Golden Penny","1kg",2500],[0,"0106","Oat Flakes","Bokku Essentials","500g",2800],[1,"0201","Vegetable Cooking Oil","Bokku Essentials","1L",3400],[1,"0202","Palm Oil","Bokku Essentials","1L",3100],[1,"0203","Tomato Paste Sachet","Generic","70g",300],[1,"0204","Curry Powder","Generic","100g",800],[1,"0205","Thyme","Generic","50g",900],[1,"0206","Iodized Table Salt","Bokku Essentials","1kg",750],[2,"0301","Corn Flakes","Kellogg's","300g",3500],[2,"0302","Golden Morn","Nestle","450g",3700],[2,"0303","Chocolate Drink Powder","Milo","400g",4800],[2,"0304","Tea Bags","Lipton","25 bags",1700],[2,"0305","Granulated Sugar","Bokku Essentials","1kg",1800],[2,"0306","Peanut Butter","Generic","340g",3200],[3,"0401","Powdered Milk","Peak","400g",6200],[3,"0402","Evaporated Milk","Peak","150ml",1250],[3,"0403","Yoghurt Drink","Generic","500ml",1650],[3,"0404","Cheddar Cheese","Generic","200g",3800],[3,"0405","Butter Spread","Generic","250g",2800],[4,"0501","Bottled Water","Generic","75cl",350],[4,"0502","Packaged Water","Generic","12 x 75cl",4000],[4,"0503","Orange Juice","Generic","1L",2500],[4,"0504","Malt Drink","Generic","33cl",750],[4,"0505","Cola Drink","Generic","50cl",650],[4,"0506","Instant Coffee","Nescafe","50g",3900],[5,"0601","Cream Crackers","Generic","200g",900],[5,"0602","Plantain Chips","Generic","100g",850],[5,"0603","Groundnuts","Bokku Essentials","200g",1000],[5,"0604","Shortbread Biscuits","Generic","200g",1800],[5,"0605","Popcorn","Generic","100g",700],[6,"0701","Bath Soap","Dettol","100g",1200],[6,"0702","Toothpaste","Closeup","140g",1900],[6,"0703","Toothbrush","Generic","1 piece",950],[6,"0704","Body Lotion","Nivea","400ml",5200],[6,"0705","Shampoo","Generic","400ml",3400],[6,"0706","Sanitary Pads","Always","8 pads",2100],[7,"0801","Laundry Detergent","Ariel","400g",2250],[7,"0802","Dishwashing Liquid","Generic","500ml",1800],[7,"0803","Bleach","Generic","1L",1800],[7,"0804","Toilet Tissue","Generic","4 rolls",2400],[7,"0805","Hand Wash","Generic","500ml",2400],[7,"0806","Bin Liners","Generic","20 pieces",1600],[8,"0901","Baked Beans","Generic","400g",1800],[8,"0902","Sardines","Titus","125g",1500],[8,"0903","Corned Beef","Generic","198g",3100],[8,"0904","Sweet Corn","Generic","340g",1600],[8,"0905","Instant Noodles","Indomie","70g",450],[8,"0906","Instant Noodles Pack","Indomie","40 x 70g",17000],[9,"1001","Fresh Tomatoes","Bokku Fresh","1kg",2600],[9,"1002","Fresh Onions","Bokku Fresh","1kg",1900],[9,"1003","Irish Potatoes","Bokku Fresh","1kg",2600],[9,"1004","Fresh Carrots","Bokku Fresh","500g",1400],[9,"1005","Ripe Bananas","Bokku Fresh","1kg",1700],[9,"1006","Red Pepper","Bokku Fresh","500g",1600]]


class Command(BaseCommand):
    help = "Add 58 demonstration supermarket products and optional per-store stock."

    def add_arguments(self, parser):
        parser.add_argument(
            "--store-code", help="Seed inventory for a single existing store code."
        )
        parser.add_argument(
            "--all-stores", action="store_true",
            help="Seed inventory for all active stores."
        )
        parser.add_argument(
            "--quantity", type=int, default=25,
            help="Starting physical stock for newly created inventory rows."
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["quantity"] < 0:
            raise CommandError("--quantity must be non-negative.")
        if options["store_code"] and options["all_stores"]:
            raise CommandError("Choose --store-code or --all-stores, not both.")

        if options["store_code"]:
            stores = list(Store.objects.filter(
                code=options["store_code"], is_active=True
            ))
            if not stores:
                raise CommandError("Active store with that code was not found.")
        elif options["all_stores"]:
            stores = list(Store.objects.filter(is_active=True))
            if not stores:
                raise CommandError("No active stores are available.")
        else:
            stores = []

        categories = {}
        created_categories = created_products = created_inventory = 0

        for name, order in CATEGORIES:
            category, created = Category.objects.get_or_create(
                slug=slugify(name),
                defaults={
                    "name": name,
                    "sort_order": order,
                    "is_active": True,
                },
            )
            categories[order - 1] = category
            created_categories += int(created)

        for category_index, code, name, brand, size, amount in PRODUCTS:
            sku = f"BKM-DEMO-{code}"
            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    "category": categories[category_index],
                    "name": name,
                    "slug": f"demo-{slugify(name)}-{code}",
                    "brand": brand,
                    "size": size,
                    "description": "Demonstration product. Verify description, supplier, actual price, and image before publishing.",
                    "is_active": True,
                },
            )
            created_products += int(created)

            for store in stores:
                inventory, added = StoreInventory.objects.get_or_create(
                    store=store,
                    product=product,
                    defaults={
                        "price": Decimal(amount),
                        "compare_at_price": None,
                        "quantity": options["quantity"],
                        "reserved_quantity": 0,
                        "is_available": True,
                    },
                )
                if added:
                    created_inventory += 1
                    if inventory.quantity:
                        InventoryMovement.objects.create(
                            inventory=inventory,
                            movement_type=InventoryMovement.Type.INITIAL_STOCK,
                            quantity_change=inventory.quantity,
                            quantity_before=0,
                            quantity_after=inventory.quantity,
                            reserved_before=0,
                            reserved_after=0,
                            reason="Initial demonstration catalog stock",
                            reference=f"DEMO-{code}",
                        )

        self.stdout.write(self.style.SUCCESS(
            f"Created {created_categories} categories, {created_products} products, "
            f"{created_inventory} store inventory records. "
            "Existing items, prices, and quantities were preserved."
        ))
        if not stores:
            self.stdout.write(
                "No inventory created: pass --store-code YOUR_STORE or --all-stores "
                "to make these products purchasable in a store."
            )
        self.stdout.write(
            "Warning: demonstration prices, brands and availability are not verified."
        )
