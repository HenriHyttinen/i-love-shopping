from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.conf import settings

from catalog.models import Product, ProductImage


class Command(BaseCommand):
    help = "Attach a local GPU image to the NexCore RTX 7060 product"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default=None,
            help="Path to the image file (defaults to repo root screenshot)",
        )

    def handle(self, *args, **options):
        product = Product.objects.filter(name__icontains="RTX 7060").first()
        if not product:
            self.stdout.write(self.style.ERROR("GPU product not found"))
            return

        path = options["path"]
        if path:
            image_path = Path(path)
        else:
            image_path = settings.BASE_DIR.parent / "Näyttökuva 2026-01-12 184431.png"

        if not image_path.exists():
            self.stdout.write(self.style.ERROR(f"Image not found: {image_path}"))
            return

        if product.images.exists():
            self.stdout.write(self.style.WARNING("Product already has images"))
            return

        content = ContentFile(image_path.read_bytes(), name="gpu.png")
        ProductImage.objects.create(product=product, image=content, alt_text="GPU image")
        self.stdout.write(self.style.SUCCESS("GPU image attached"))
