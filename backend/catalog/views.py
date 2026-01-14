from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Case, IntegerField, Value, When
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import ProductFilter
from .models import Brand, Category, Product
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    ProductSerializer,
    ProductImageUploadSerializer,
)


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
        serializer.save(product=product, image=processed)
        return Response(serializer.data, status=201)

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
