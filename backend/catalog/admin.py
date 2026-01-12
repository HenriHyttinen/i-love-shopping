from django.contrib import admin

from .models import Brand, Category, Product, ProductImage, ProductSpec


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "stock_quantity", "brand", "category")
    list_filter = ("brand", "category")
    search_fields = ("name",)
    inlines = [ProductImageInline]


admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(ProductSpec)
