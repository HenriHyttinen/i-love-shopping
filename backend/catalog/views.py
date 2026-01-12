from django.db.models.functions import Lower
from rest_framework import generics, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import ProductFilter
from django.shortcuts import get_object_or_404
from .models import Brand, Category, Product
from .serializers import BrandSerializer, CategorySerializer, ProductSerializer, ProductImageUploadSerializer


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all().select_related("category", "brand").prefetch_related("images")
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = ProductFilter
    search_fields = ["name", "description", "brand__name", "category__name"]
    ordering_fields = ["price", "rating", "name"]


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
        serializer = ProductImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        return Response(serializer.data, status=201)
