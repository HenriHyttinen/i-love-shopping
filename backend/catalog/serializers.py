from django.conf import settings
from rest_framework import serializers

from .models import Brand, Category, Product, ProductImage, ProductSpec


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt_text")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name")


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    specs = serializers.SerializerMethodField()

    def get_specs(self, obj):
        return {spec.key: spec.value for spec in obj.specs.all()}

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "sku",
            "description",
            "price",
            "stock_quantity",
            "category",
            "brand",
            "rating",
            "is_active",
            "images",
            "specs",
            "weight_kg",
            "weight_lb",
            "length_cm",
            "width_cm",
            "height_cm",
            "length_in",
            "width_in",
            "height_in",
        )


class ProductImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt_text")

    def validate_image(self, value):
        if value.content_type not in settings.CATALOG_IMAGE_ALLOWED_TYPES:
            raise serializers.ValidationError("Only PNG or JPEG images are allowed.")
        if value.size > settings.CATALOG_IMAGE_MAX_BYTES:
            raise serializers.ValidationError("Image file is too large.")
        return value
