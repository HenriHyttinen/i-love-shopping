from django.urls import path

from .views import (
    BrandListView,
    CategoryListView,
    ProductImageUploadView,
    ProductDetailView,
    ProductListView,
    SearchSuggestView,
)

urlpatterns = [
    path("products/", ProductListView.as_view(), name="product_list"),
    path("products/<int:pk>/", ProductDetailView.as_view(), name="product_detail"),
    path("products/<int:product_id>/images/", ProductImageUploadView.as_view(), name="product_image_upload"),
    path("categories/", CategoryListView.as_view(), name="category_list"),
    path("brands/", BrandListView.as_view(), name="brand_list"),
    path("suggest/", SearchSuggestView.as_view(), name="search_suggest"),
]
