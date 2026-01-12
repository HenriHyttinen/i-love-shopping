import base64
import tempfile
from io import BytesIO

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from PIL import Image

from catalog.models import Brand, Category, Product
from users.models import User


class CatalogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Processors", slug="processors")
        self.brand = Brand.objects.create(name="IronChip")
        Product.objects.create(
            name="IronChip i9-13900",
            description="High-end CPU",
            price=499.99,
            stock_quantity=5,
            category=self.category,
            brand=self.brand,
            rating=4.8,
            weight_kg=0.05,
            weight_lb=0.11,
            length_cm=4.5,
            width_cm=4.5,
            height_cm=0.5,
            length_in=1.77,
            width_in=1.77,
            height_in=0.2,
        )
        Product.objects.create(
            name="IronChip i5-12400",
            description="Budget CPU",
            price=189.99,
            stock_quantity=12,
            category=self.category,
            brand=self.brand,
            rating=4.1,
            weight_kg=0.05,
            weight_lb=0.11,
            length_cm=4.5,
            width_cm=4.5,
            height_cm=0.5,
            length_in=1.77,
            width_in=1.77,
            height_in=0.2,
        )

    def test_product_list(self):
        response = self.client.get("/api/catalog/products/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        response = self.client.get("/api/catalog/products/?search=budget")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_product_detail(self):
        product = Product.objects.first()
        response = self.client.get(f"/api/catalog/products/{product.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], product.id)

    def test_product_detail_missing(self):
        response = self.client.get("/api/catalog/products/9999/")
        self.assertEqual(response.status_code, 404)

    def test_product_filtering(self):
        response = self.client.get("/api/catalog/products/?min_price=400")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get("/api/catalog/products/?min_price=abc")
        self.assertEqual(response.status_code, 400)

    def test_product_ordering(self):
        response = self.client.get("/api/catalog/products/?ordering=price")
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(response.data[0]["price"], response.data[1]["price"])
        response = self.client.get("/api/catalog/products/?ordering=-price")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data[0]["price"], response.data[1]["price"])
        response = self.client.get("/api/catalog/products/?ordering=name")
        self.assertEqual(response.status_code, 200)

    def test_product_category_filter(self):
        response = self.client.get("/api/catalog/products/?category=processors")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        response = self.client.get("/api/catalog/products/?brand=ironchip")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        response = self.client.get("/api/catalog/products/?rating=4.5")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_categories_and_brands(self):
        response = self.client.get("/api/catalog/categories/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get("/api/catalog/brands/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_search_suggest(self):
        response = self.client.get("/api/catalog/suggest/?q=iron")
        self.assertEqual(response.status_code, 200)
        self.assertIn("IronChip i9-13900", response.data)
        empty = self.client.get("/api/catalog/suggest/?q=")
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.data, [])
        self.assertLessEqual(len(response.data), 8)

    def test_security_input(self):
        response = self.client.get("/api/catalog/products/?search=%27%20OR%201%3D1--")
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/api/catalog/products/?ordering=not_a_field")
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/api/catalog/products/?category[]=processors")
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/api/catalog/products/?min_price=-10")
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/api/catalog/products/?max_price=abc")
        self.assertEqual(response.status_code, 400)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_image_upload_admin(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="AdminPass123!")
        self.client.force_authenticate(user=admin)

        image = Image.new("RGB", (1, 1), color=(255, 0, 0))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        upload = SimpleUploadedFile("sample.png", buffer.read(), content_type="image/png")
        response = self.client.post(
            f"/api/catalog/products/{Product.objects.first().id}/images/",
            {"image": upload, "alt_text": "Sample"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)

        for _ in range(4):
            image = Image.new("RGB", (1, 1), color=(255, 0, 0))
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            extra = SimpleUploadedFile("extra.png", buffer.read(), content_type="image/png")
            self.client.post(
                f"/api/catalog/products/{Product.objects.first().id}/images/",
                {"image": extra, "alt_text": "Extra"},
                format="multipart",
            )
        image = Image.new("RGB", (1, 1), color=(255, 0, 0))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        extra = SimpleUploadedFile("limit.png", buffer.read(), content_type="image/png")
        limit = self.client.post(
            f"/api/catalog/products/{Product.objects.first().id}/images/",
            {"image": extra, "alt_text": "Limit"},
            format="multipart",
        )
        self.assertEqual(limit.status_code, 400)

    def test_image_upload_denied_for_non_admin(self):
        user = User.objects.create_user(email="user@example.com", password="UserPass123!")
        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/api/catalog/products/{Product.objects.first().id}/images/",
            {},
            format="multipart",
        )
        self.assertEqual(response.status_code, 403)

    def test_image_upload_requires_auth(self):
        response = self.client.post(
            f"/api/catalog/products/{Product.objects.first().id}/images/",
            {},
            format="multipart",
        )
        self.assertEqual(response.status_code, 401)
