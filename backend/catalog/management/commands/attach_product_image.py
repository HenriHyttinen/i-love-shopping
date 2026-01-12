from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from catalog.models import Product, ProductImage


class Command(BaseCommand):
    help = "Attach a local image to a product by id or name"

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, default=None)
        parser.add_argument("--product-name", type=str, default=None)
        parser.add_argument("--path", type=str, required=True)
        parser.add_argument("--alt", type=str, default="Product image")

    def handle(self, *args, **options):
        product_id = options["product_id"]
        product_name = options["product_name"]
        if not product_id and not product_name:
            self.stdout.write(self.style.ERROR("Provide --product-id or --product-name"))
            return

        if product_id:
            product = Product.objects.filter(id=product_id).first()
        else:
            product = Product.objects.filter(name__icontains=product_name).first()

        if not product:
            self.stdout.write(self.style.ERROR("Product not found"))
            return

        image_path = Path(options["path"])
        if not image_path.exists():
            self.stdout.write(self.style.ERROR(f"Image not found: {image_path}"))
            return

        content = ContentFile(image_path.read_bytes(), name=image_path.name)
        ProductImage.objects.create(product=product, image=content, alt_text=options["alt"])
        self.stdout.write(self.style.SUCCESS("Image attached"))
