from django.conf import settings
from rest_framework import serializers

from commerce.models import Order, OrderItem

from .models import Brand, Category, Product, ProductImage, ProductSpec, Review


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


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    helpful_votes = serializers.SerializerMethodField()
    voted_helpful = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = (
            "id",
            "product",
            "user",
            "user_name",
            "rating",
            "comment",
            "helpful_votes",
            "voted_helpful",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "product", "user", "user_name", "helpful_votes", "voted_helpful", "created_at", "updated_at")

    def get_user_name(self, obj):
        return obj.user.full_name or obj.user.email

    def get_helpful_votes(self, obj):
        annotated = getattr(obj, "helpful_votes_count", None)
        if annotated is not None:
            return annotated
        return obj.helpful_votes.count()

    def get_voted_helpful(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.helpful_votes.filter(user=request.user).exists()

    def validate_comment(self, value):
        comment = (value or "").strip()
        if len(comment) < 3:
            raise serializers.ValidationError("Review text is too short.")
        return comment

    def validate(self, attrs):
        request = self.context.get("request")
        product = self.context.get("product")
        if not request or not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError("Login is required to leave a review.")
        if not product:
            raise serializers.ValidationError("Product is required.")

        purchased = OrderItem.objects.filter(
            order__user=request.user,
            order__status=Order.STATUS_PAYMENT_SUCCESSFUL,
            product=product,
        ).exists()
        if not purchased:
            raise serializers.ValidationError("Only customers who bought this product can leave a review.")

        if Review.objects.filter(product=product, user=request.user).exists():
            raise serializers.ValidationError("You have already reviewed this product.")
        return attrs


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


class CategoryAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")
        read_only_fields = ("id",)


class ProductAdminSerializer(serializers.ModelSerializer):
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
            "is_active",
            "weight_kg",
            "weight_lb",
            "length_cm",
            "width_cm",
            "height_cm",
            "length_in",
            "width_in",
            "height_in",
        )
        read_only_fields = ("id",)
