import csv
import json
from io import StringIO

from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Case, IntegerField, Value, When
from django.db.models import Count
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import ProductFilter
from .models import Brand, Category, Product, Review, ReviewHelpfulVote
from .serializers import (
    CategoryAdminSerializer,
    BrandSerializer,
    CategorySerializer,
    ProductAdminSerializer,
    ProductSerializer,
    ProductImageUploadSerializer,
    ProductImageSerializer,
    ReviewSerializer,
)
from users.permissions import IsAdminWith2FA


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all().select_related("category", "brand").prefetch_related("images")
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = ProductFilter
    search_fields = ["name", "description", "brand__name", "category__name"]
    ordering_fields = ["price", "rating", "name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        ordering = self.request.query_params.get("ordering", "")
        search = self.request.query_params.get("search", "").strip()
        if ordering == "relevance" and search:
            return queryset.annotate(
                relevance_rank=Case(
                    When(name__istartswith=search, then=Value(0)),
                    When(name__icontains=search, then=Value(1)),
                    When(description__icontains=search, then=Value(2)),
                    When(brand__name__icontains=search, then=Value(3)),
                    When(category__name__icontains=search, then=Value(4)),
                    default=Value(5),
                    output_field=IntegerField(),
                )
            ).order_by("relevance_rank", "name")
        return queryset


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.all().select_related("category", "brand").prefetch_related("images")
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class BrandListView(generics.ListAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [permissions.AllowAny]


class SearchSuggestView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response([])
        suggestions = (
            Product.objects.annotate(name_lower=Lower("name"))
            .filter(name_lower__icontains=query.lower())
            .values_list("name", flat=True)
            .distinct()[:8]
        )
        return Response(list(suggestions))


class ProductImageUploadView(APIView):
    permission_classes = [permissions.IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        if product.images.count() >= settings.CATALOG_IMAGE_MAX_COUNT:
            return Response({"detail": "Image limit reached."}, status=400)
        serializer = ProductImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = serializer.validated_data["image"]
        processed = self._process_image(image)
        created = serializer.save(product=product, image=processed)
        return Response(ProductImageSerializer(created).data, status=201)

    def _process_image(self, image):
        from PIL import Image

        img = Image.open(image)
        img_format = "PNG" if img.format == "PNG" else "JPEG"

        if img_format == "JPEG":
            img = img.convert("RGB")

        max_dim = settings.CATALOG_IMAGE_MAX_DIM
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim))

        buffer = BytesIO()
        if img_format == "PNG":
            img.save(buffer, format="PNG", optimize=True)
        else:
            img.save(buffer, format="JPEG", quality=85, optimize=True)
        buffer.seek(0)
        return ContentFile(buffer.read(), name=image.name)


class ProductReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        product_id = self.kwargs["product_id"]
        return (
            Review.objects.filter(product_id=product_id)
            .select_related("user")
            .prefetch_related("helpful_votes")
            .annotate(helpful_votes_count=Count("helpful_votes"))
            .order_by("-helpful_votes_count", "-created_at")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["product"] = get_object_or_404(Product, id=self.kwargs["product_id"], is_active=True)
        return context

    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=401)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
            product=get_object_or_404(Product, id=self.kwargs["product_id"], is_active=True),
        )


class ReviewHelpfulVoteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, review_id):
        review = get_object_or_404(Review, id=review_id)
        vote, created = ReviewHelpfulVote.objects.get_or_create(review=review, user=request.user)
        if not created:
            vote.delete()
            return Response({"detail": "Helpful vote removed.", "voted_helpful": False})
        return Response({"detail": "Helpful vote added.", "voted_helpful": True}, status=201)


class AdminReviewModerationView(APIView):
    permission_classes = [IsAdminWith2FA]

    def delete(self, request, review_id):
        review = Review.objects.filter(id=review_id).first()
        if not review:
            return Response({"detail": "Review not found."}, status=404)
        review.delete()
        return Response(status=204)


class AdminProductBulkUploadView(APIView):
    permission_classes = [IsAdminWith2FA]

    REQUIRED_FIELDS = {
        "name",
        "description",
        "price",
        "stock_quantity",
        "category",
        "brand",
        "weight_kg",
        "weight_lb",
        "length_cm",
        "width_cm",
        "height_cm",
        "length_in",
        "width_in",
        "height_in",
    }

    def post(self, request):
        fmt = str(request.data.get("format", "json")).strip().lower()
        raw = request.data.get("payload", "")
        if not raw:
            return Response({"detail": "payload is required."}, status=400)

        if fmt == "json":
            try:
                rows = json.loads(raw)
            except Exception:
                return Response({"detail": "Invalid JSON payload."}, status=400)
            if not isinstance(rows, list):
                return Response({"detail": "JSON payload must be an array of products."}, status=400)
        elif fmt == "csv":
            reader = csv.DictReader(StringIO(raw))
            rows = list(reader)
        else:
            return Response({"detail": "format must be json or csv."}, status=400)

        created = 0
        updated = 0
        errors = []
        for idx, row in enumerate(rows, start=1):
            try:
                missing = [field for field in self.REQUIRED_FIELDS if str(row.get(field, "")).strip() == ""]
                if missing:
                    errors.append({"row": idx, "detail": f"Missing fields: {', '.join(sorted(missing))}"})
                    continue
                category, _ = Category.objects.get_or_create(
                    slug=str(row["category"]).strip().lower().replace(" ", "-"),
                    defaults={"name": str(row["category"]).strip()},
                )
                brand, _ = Brand.objects.get_or_create(name=str(row["brand"]).strip())
                defaults = {
                    "description": str(row["description"]).strip(),
                    "price": row["price"],
                    "stock_quantity": int(row["stock_quantity"]),
                    "category": category,
                    "brand": brand,
                    "weight_kg": row["weight_kg"],
                    "weight_lb": row["weight_lb"],
                    "length_cm": row["length_cm"],
                    "width_cm": row["width_cm"],
                    "height_cm": row["height_cm"],
                    "length_in": row["length_in"],
                    "width_in": row["width_in"],
                    "height_in": row["height_in"],
                }
                product, was_created = Product.objects.update_or_create(
                    name=str(row["name"]).strip(),
                    defaults=defaults,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            except Exception as exc:
                errors.append({"row": idx, "detail": f"Invalid row: {exc.__class__.__name__}"})

        return Response(
            {
                "created": created,
                "updated": updated,
                "failed": len(errors),
                "errors": errors[:50],
            }
        )


class AdminCategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminWith2FA]
    serializer_class = CategoryAdminSerializer
    queryset = Category.objects.all().order_by("name")


class AdminCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminWith2FA]
    serializer_class = CategoryAdminSerializer
    queryset = Category.objects.all()


class AdminProductListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminWith2FA]
    serializer_class = ProductAdminSerializer
    queryset = Product.objects.select_related("category", "brand").all().order_by("name")


class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminWith2FA]
    serializer_class = ProductAdminSerializer
    queryset = Product.objects.select_related("category", "brand").all()
