from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import Avg
from django.core.validators import MaxValueValidator, MinValueValidator


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(blank=True)
    sku = models.CharField(max_length=50, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products")
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    weight_kg = models.DecimalField(max_digits=6, decimal_places=2)
    weight_lb = models.DecimalField(max_digits=6, decimal_places=2)

    length_cm = models.DecimalField(max_digits=6, decimal_places=2)
    width_cm = models.DecimalField(max_digits=6, decimal_places=2)
    height_cm = models.DecimalField(max_digits=6, decimal_places=2)

    length_in = models.DecimalField(max_digits=6, decimal_places=2)
    width_in = models.DecimalField(max_digits=6, decimal_places=2)
    height_in = models.DecimalField(max_digits=6, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    VARIANT_SIZES = {
        "thumbnail": (120, 120),
        "medium": (360, 360),
    }

    def _variant_name(self, size_key):
        source = Path(self.image.name)
        ext = ".png" if source.suffix.lower() == ".png" else ".jpg"
        stem = source.stem
        return str(source.parent / f"{stem}_{size_key}{ext}")

    def _generate_variants(self):
        if not self.image:
            return
        from PIL import Image

        with self.image.open("rb") as fp:
            source = Image.open(fp)
            source.load()

        for size_key, dimensions in self.VARIANT_SIZES.items():
            target_name = self._variant_name(size_key)
            if self.image.storage.exists(target_name):
                continue
            variant = source.copy()
            if variant.mode not in ("RGB", "RGBA"):
                variant = variant.convert("RGB")
            variant.thumbnail(dimensions)

            output = BytesIO()
            ext = Path(target_name).suffix.lower()
            if ext == ".png":
                variant.save(output, format="PNG", optimize=True)
            else:
                if variant.mode == "RGBA":
                    variant = variant.convert("RGB")
                variant.save(output, format="JPEG", quality=85, optimize=True)
            output.seek(0)
            self.image.storage.save(target_name, ContentFile(output.read()))

    def save(self, *args, **kwargs):
        is_create = self._state.adding
        super().save(*args, **kwargs)
        if is_create and self.image:
            self._generate_variants()

    def delete(self, *args, **kwargs):
        for size_key in self.VARIANT_SIZES.keys():
            name = self._variant_name(size_key)
            if self.image.storage.exists(name):
                self.image.storage.delete(name)
        super().delete(*args, **kwargs)

    def variant_url(self, size_key):
        if size_key == "full":
            return self.image.url
        name = self._variant_name(size_key)
        if self.image.storage.exists(name):
            return self.image.storage.url(name)
        return self.image.url


class ProductSpec(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="specs")
    key = models.CharField(max_length=60)
    value = models.CharField(max_length=120)

    class Meta:
        unique_together = ("product", "key")

    def __str__(self):
        return f"{self.product.name} {self.key}"

    def __str__(self):
        return f"{self.product.name} image"


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product", "user")
        ordering = ("-created_at",)

    @staticmethod
    def refresh_product_rating(product_id: int) -> None:
        avg_value = Review.objects.filter(product_id=product_id).aggregate(avg=Avg("rating"))["avg"]
        if avg_value is None:
            normalized = Decimal("0.00")
        else:
            normalized = Decimal(str(avg_value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        Product.objects.filter(id=product_id).update(rating=normalized)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Review.refresh_product_rating(self.product_id)

    def delete(self, *args, **kwargs):
        product_id = self.product_id
        super().delete(*args, **kwargs)
        Review.refresh_product_rating(product_id)


class ReviewHelpfulVote(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="helpful_votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="review_helpful_votes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("review", "user")
