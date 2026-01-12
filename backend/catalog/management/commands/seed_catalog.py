from django.core.management.base import BaseCommand

from catalog.models import Brand, Category, Product


class Command(BaseCommand):
    help = "Seed initial hardware catalog data"

    def handle(self, *args, **options):
        categories = [
            ("Graphics Cards", "graphics-cards"),
            ("Processors", "processors"),
            ("Motherboards", "motherboards"),
            ("Storage", "storage"),
            ("Peripherals", "peripherals"),
        ]
        brands = ["NexCore", "ByteForge", "VoltStream", "IronChip", "PixelPeak"]

        category_objs = {}
        for name, slug in categories:
            category_objs[slug], _ = Category.objects.get_or_create(name=name, slug=slug)

        brand_objs = {}
        for name in brands:
            brand_objs[name], _ = Brand.objects.get_or_create(name=name)

        products = [
            {
                "name": "NexCore RTX 7060",
                "description": "Solid midrange GPU for 1080p gaming and creative work.",
                "price": 329.99,
                "stock_quantity": 42,
                "category": category_objs["graphics-cards"],
                "brand": brand_objs["NexCore"],
                "rating": 4.2,
                "weight_kg": 1.2,
                "weight_lb": 2.6,
                "length_cm": 24.0,
                "width_cm": 12.0,
                "height_cm": 4.5,
                "length_in": 9.45,
                "width_in": 4.72,
                "height_in": 1.77,
            },
            {
                "name": "IronChip i7-12700",
                "description": "12-core CPU for gaming and multitasking.",
                "price": 279.00,
                "stock_quantity": 30,
                "category": category_objs["processors"],
                "brand": brand_objs["IronChip"],
                "rating": 4.6,
                "weight_kg": 0.05,
                "weight_lb": 0.11,
                "length_cm": 4.5,
                "width_cm": 4.5,
                "height_cm": 0.5,
                "length_in": 1.77,
                "width_in": 1.77,
                "height_in": 0.2,
            },
            {
                "name": "ByteForge B650 Board",
                "description": "ATX motherboard with Wi-Fi and PCIe 4.0 support.",
                "price": 169.50,
                "stock_quantity": 18,
                "category": category_objs["motherboards"],
                "brand": brand_objs["ByteForge"],
                "rating": 4.0,
                "weight_kg": 0.9,
                "weight_lb": 1.98,
                "length_cm": 30.5,
                "width_cm": 24.4,
                "height_cm": 4.0,
                "length_in": 12.0,
                "width_in": 9.6,
                "height_in": 1.57,
            },
            {
                "name": "VoltStream NVMe 1TB",
                "description": "Fast PCIe Gen4 SSD with heatsink.",
                "price": 94.99,
                "stock_quantity": 60,
                "category": category_objs["storage"],
                "brand": brand_objs["VoltStream"],
                "rating": 4.4,
                "weight_kg": 0.03,
                "weight_lb": 0.07,
                "length_cm": 8.0,
                "width_cm": 2.2,
                "height_cm": 0.2,
                "length_in": 3.15,
                "width_in": 0.87,
                "height_in": 0.08,
            },
            {
                "name": "PixelPeak Mechanical Keyboard",
                "description": "Tactile switch keyboard with white backlight.",
                "price": 59.99,
                "stock_quantity": 75,
                "category": category_objs["peripherals"],
                "brand": brand_objs["PixelPeak"],
                "rating": 3.9,
                "weight_kg": 0.8,
                "weight_lb": 1.76,
                "length_cm": 44.0,
                "width_cm": 13.0,
                "height_cm": 3.5,
                "length_in": 17.32,
                "width_in": 5.12,
                "height_in": 1.38,
            },
        ]

        for data in products:
            Product.objects.get_or_create(name=data["name"], defaults=data)

        self.stdout.write(self.style.SUCCESS("Catalog seed complete"))
