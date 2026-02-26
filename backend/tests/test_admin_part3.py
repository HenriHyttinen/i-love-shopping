from decimal import Decimal

import pyotp
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Brand, Category, Product, Review
from commerce.models import DeliveryOption, Order, RefundRequest
from users.models import User


class AdminPart3Tests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Graphics Cards", slug="graphics-cards")
        self.brand = Brand.objects.create(name="NexCore")
        self.product = Product.objects.create(
            name="NexCore RTX 5070",
            description="GPU",
            price=Decimal("599.99"),
            stock_quantity=8,
            category=self.category,
            brand=self.brand,
            rating=Decimal("4.80"),
            weight_kg=Decimal("1.20"),
            weight_lb=Decimal("2.65"),
            length_cm=Decimal("30.00"),
            width_cm=Decimal("12.00"),
            height_cm=Decimal("4.00"),
            length_in=Decimal("11.80"),
            width_in=Decimal("4.70"),
            height_in=Decimal("1.60"),
        )

    def _create_admin(self, *, with_2fa=True, email="admin@example.com"):
        user = User.objects.create_user(
            email=email,
            password="AdminPass123!",
            full_name="Admin User",
            is_staff=True,
            role=User.ROLE_ADMIN,
        )
        if with_2fa:
            user.otp_secret = pyotp.random_base32()
            user.is_2fa_enabled = True
            user.save(update_fields=["otp_secret", "is_2fa_enabled"])
        return user

    def _admin_auth_header(self, email="admin@example.com"):
        admin = self._create_admin(with_2fa=True, email=email)
        code = pyotp.TOTP(admin.otp_secret).now()
        login = self.client.post(
            "/api/auth/login/",
            {"email": admin.email, "password": "AdminPass123!", "code": code},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        return {"HTTP_AUTHORIZATION": f"Bearer {login.data['access']}"}

    def test_staff_login_requires_2fa(self):
        self._create_admin(with_2fa=False)
        login = self.client.post(
            "/api/auth/login/",
            {"email": "admin@example.com", "password": "AdminPass123!"},
            format="json",
        )
        self.assertEqual(login.status_code, 400)
        self.assertIn("Admin accounts must enable 2FA", str(login.data))

    def test_admin_user_role_update_requires_admin_2fa_permission(self):
        admin_without_2fa = self._create_admin(with_2fa=False)
        target = User.objects.create_user(email="target@example.com", password="StrongPass123!")
        self.client.force_authenticate(user=admin_without_2fa)
        denied = self.client.post(
            f"/api/auth/admin/users/{target.id}/role/",
            {"role": User.ROLE_SUPPORT},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

        authed = APIClient()
        headers = self._admin_auth_header(email="admin2@example.com")
        ok = authed.post(
            f"/api/auth/admin/users/{target.id}/role/",
            {"role": User.ROLE_SUPPORT},
            format="json",
            **headers,
        )
        self.assertEqual(ok.status_code, 200)
        target.refresh_from_db()
        self.assertEqual(target.role, User.ROLE_SUPPORT)
        self.assertTrue(target.is_staff)

    def test_admin_delivery_options_crud_and_checkout_summary(self):
        headers = self._admin_auth_header()
        create = self.client.post(
            "/api/commerce/admin/delivery-options/",
            {"code": "priority", "label": "Priority", "cost": "14.90", "is_active": True},
            format="json",
            **headers,
        )
        self.assertEqual(create.status_code, 201)
        option_id = create.data["id"]

        summary = self.client.get("/api/commerce/checkout/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertTrue(any(o["code"] == "priority" for o in summary.data["shipping_options"]))

        patch = self.client.patch(
            f"/api/commerce/admin/delivery-options/{option_id}/",
            {"cost": "16.90"},
            format="json",
            **headers,
        )
        self.assertEqual(patch.status_code, 200)
        self.assertEqual(str(patch.data["cost"]), "16.90")

        delete = self.client.delete(
            f"/api/commerce/admin/delivery-options/{option_id}/",
            **headers,
        )
        self.assertEqual(delete.status_code, 204)

    def test_refund_request_and_admin_status_update(self):
        buyer = User.objects.create_user(email="buyer@example.com", password="StrongPass123!")
        order = Order.objects.create(
            user=buyer,
            status=Order.STATUS_PAYMENT_SUCCESSFUL,
            payment_method="stripe_sandbox",
            shipping_option=Order.SHIPPING_STANDARD,
            shipping_cost=Decimal("7.90"),
            subtotal=Decimal("599.99"),
            total=Decimal("607.89"),
        )

        buyer_client = APIClient()
        buyer_client.force_authenticate(user=buyer)
        created = buyer_client.post(
            "/api/commerce/refunds/",
            {"order": order.id, "reason": "Item arrived damaged"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        refund_id = created.data["id"]
        self.assertEqual(created.data["status"], RefundRequest.STATUS_PENDING)

        headers = self._admin_auth_header()
        listed = self.client.get("/api/commerce/admin/refunds/", **headers)
        self.assertEqual(listed.status_code, 200)
        self.assertTrue(any(r["id"] == refund_id for r in listed.data))

        updated = self.client.post(
            f"/api/commerce/admin/refunds/{refund_id}/status/",
            {"status": RefundRequest.STATUS_APPROVED, "note": "Approved by support"},
            format="json",
            **headers,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["status"], RefundRequest.STATUS_APPROVED)

    def test_admin_order_list_endpoint(self):
        headers = self._admin_auth_header(email="admin-orders@example.com")
        listed = self.client.get("/api/commerce/admin/orders/", **headers)
        self.assertEqual(listed.status_code, 200)
        self.assertIsInstance(listed.data, list)

    def test_admin_bulk_upload_and_review_moderation(self):
        headers = self._admin_auth_header()
        payload = """
[
  {
    "name": "NexCore RTX 4050",
    "description": "Entry GPU",
    "price": "249.99",
    "stock_quantity": 5,
    "category": "Graphics Cards",
    "brand": "NexCore",
    "weight_kg": "0.90",
    "weight_lb": "1.98",
    "length_cm": "24",
    "width_cm": "11",
    "height_cm": "3",
    "length_in": "9.4",
    "width_in": "4.3",
    "height_in": "1.2"
  }
]
        """.strip()
        bulk = self.client.post(
            "/api/catalog/admin/products/bulk-upload/",
            {"format": "json", "payload": payload},
            format="json",
            **headers,
        )
        self.assertEqual(bulk.status_code, 200)
        self.assertEqual(bulk.data["created"], 1)
        self.assertTrue(Product.objects.filter(name="NexCore RTX 4050").exists())

        reviewer = User.objects.create_user(email="rev@example.com", password="StrongPass123!")
        paid = Order.objects.create(
            user=reviewer,
            status=Order.STATUS_PAYMENT_SUCCESSFUL,
            payment_method="stripe_sandbox",
            shipping_option=Order.SHIPPING_STANDARD,
            shipping_cost=Decimal("7.90"),
            subtotal=self.product.price,
            total=self.product.price + Decimal("7.90"),
        )
        paid.items.create(
            product=self.product,
            product_name=self.product.name,
            quantity=1,
            unit_price=self.product.price,
            line_total=self.product.price,
        )
        review = Review.objects.create(product=self.product, user=reviewer, rating=4, comment="Good")

        moderation = self.client.delete(
            f"/api/catalog/admin/reviews/{review.id}/",
            **headers,
        )
        self.assertEqual(moderation.status_code, 204)
        self.assertFalse(Review.objects.filter(id=review.id).exists())

    def test_admin_category_and_product_crud(self):
        headers = self._admin_auth_header(email="admin3@example.com")
        new_category = self.client.post(
            "/api/catalog/admin/categories/",
            {"name": "Monitors", "slug": "monitors"},
            format="json",
            **headers,
        )
        self.assertEqual(new_category.status_code, 201)
        category_id = new_category.data["id"]

        product_create = self.client.post(
            "/api/catalog/admin/products/",
            {
                "name": "NexCore Vision 27",
                "slug": "nexcore-vision-27",
                "sku": "MON-27-001",
                "description": "27 inch monitor",
                "price": "199.99",
                "stock_quantity": 10,
                "category": category_id,
                "brand": self.brand.id,
                "is_active": True,
                "weight_kg": "4.10",
                "weight_lb": "9.04",
                "length_cm": "61.00",
                "width_cm": "18.00",
                "height_cm": "45.00",
                "length_in": "24.02",
                "width_in": "7.09",
                "height_in": "17.72",
            },
            format="json",
            **headers,
        )
        self.assertEqual(product_create.status_code, 201)
        product_id = product_create.data["id"]

        product_update = self.client.patch(
            f"/api/catalog/admin/products/{product_id}/",
            {"stock_quantity": 7},
            format="json",
            **headers,
        )
        self.assertEqual(product_update.status_code, 200)
        self.assertEqual(product_update.data["stock_quantity"], 7)

        product_delete = self.client.delete(
            f"/api/catalog/admin/products/{product_id}/",
            **headers,
        )
        self.assertEqual(product_delete.status_code, 204)

        category_delete = self.client.delete(
            f"/api/catalog/admin/categories/{category_id}/",
            **headers,
        )
        self.assertIn(category_delete.status_code, {204, 400})
