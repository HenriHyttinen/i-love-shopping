from io import BytesIO
from pathlib import Path
import time

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from catalog.models import Product, ProductImage


class Command(BaseCommand):
    help = "Attach tiny sample images to first products"

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Replace existing product images with new placeholders",
        )
        parser.add_argument(
            "--use-real",
            action="store_true",
            help="Prefer existing files in MEDIA_ROOT/products over placeholders",
        )

    def handle(self, *args, **options):
        from PIL import Image, ImageDraw
        from django.conf import settings

        replace = options["replace"]
        use_real = options["use_real"]
        products = Product.objects.all()
        if not products:
            self.stdout.write(self.style.WARNING("No products found"))
            return
        real_files = []
        if use_real:
            media_dir = Path(settings.MEDIA_ROOT) / "products"
            if media_dir.exists():
                real_files = sorted(
                    [
                        path
                        for path in media_dir.iterdir()
                        if path.is_file()
                        and path.suffix.lower() in {".png", ".jpg", ".jpeg"}
                        and "_sample" not in path.name
                    ]
                )
        real_iter = iter(real_files)

        for product in products:
            if product.images.exists() and not replace:
                continue
            if replace:
                product.images.all().delete()
            image_path = next(real_iter, None)
            if image_path:
                content = ContentFile(image_path.read_bytes(), name=image_path.name)
                ProductImage.objects.create(
                    product=product,
                    image=content,
                    alt_text=product.name,
                )
            else:
                img = Image.new("RGB", (360, 200), color=(230, 235, 242))
                draw = ImageDraw.Draw(img)
                draw.rectangle([10, 10, 350, 190], outline=(52, 102, 190), width=3)
                draw.text((18, 18), product.name, fill=(12, 24, 40))
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                buffer.seek(0)
                stamp = int(time.time())
                image_file = ContentFile(
                    buffer.read(), name=f"{product.id}_sample_{stamp}.png"
                )
                ProductImage.objects.create(
                    product=product, image=image_file, alt_text="Sample"
                )

        self.stdout.write(self.style.SUCCESS("Sample images added"))
