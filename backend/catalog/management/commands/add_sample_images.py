import base64

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from catalog.models import Product, ProductImage


class Command(BaseCommand):
    help = "Attach tiny sample images to first products"

    def handle(self, *args, **options):
        png_bytes = base64.b64decode(
            b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/xcAAn8B9Yw6uQAAAABJRU5ErkJggg=="
        )
        products = Product.objects.all()[:3]
        if not products:
            self.stdout.write(self.style.WARNING("No products found"))
            return

        for product in products:
            if product.images.exists():
                continue
            image_file = ContentFile(png_bytes, name=f"{product.id}_sample.png")
            ProductImage.objects.create(product=product, image=image_file, alt_text="Sample")

        self.stdout.write(self.style.SUCCESS("Sample images added"))
