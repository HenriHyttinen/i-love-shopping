from django.urls import path

from .views import (
    BrandListView,
    CategoryListView,
    ProductImageUploadView,
    ProductDetailView,
    ProductListView,
    AdminProductBulkUploadView,
    AdminProductDetailView,
    AdminProductListCreateView,
    AdminCategoryDetailView,
    AdminCategoryListCreateView,
    AdminReviewModerationView,
    ProductReviewListCreateView,
    ReviewHelpfulVoteView,
    SearchSuggestView,
)

urlpatterns = [
    path("products/", ProductListView.as_view(), name="product_list"),
    path("products/<int:pk>/", ProductDetailView.as_view(), name="product_detail"),
    path("products/<int:product_id>/images/", ProductImageUploadView.as_view(), name="product_image_upload"),
    path("products/<int:product_id>/reviews/", ProductReviewListCreateView.as_view(), name="product_reviews"),
    path("reviews/<int:review_id>/helpful/", ReviewHelpfulVoteView.as_view(), name="review_helpful_vote"),
    path("admin/reviews/<int:review_id>/", AdminReviewModerationView.as_view(), name="admin_review_moderation"),
    path("admin/products/bulk-upload/", AdminProductBulkUploadView.as_view(), name="admin_product_bulk_upload"),
    path("admin/products/", AdminProductListCreateView.as_view(), name="admin_product_list_create"),
    path("admin/products/<int:pk>/", AdminProductDetailView.as_view(), name="admin_product_detail"),
    path("admin/categories/", AdminCategoryListCreateView.as_view(), name="admin_category_list_create"),
    path("admin/categories/<int:pk>/", AdminCategoryDetailView.as_view(), name="admin_category_detail"),
    path("categories/", CategoryListView.as_view(), name="category_list"),
    path("brands/", BrandListView.as_view(), name="brand_list"),
    path("suggest/", SearchSuggestView.as_view(), name="search_suggest"),
]
