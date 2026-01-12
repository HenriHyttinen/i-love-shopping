from django.db import models


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
