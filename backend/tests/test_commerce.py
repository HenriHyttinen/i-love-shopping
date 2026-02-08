from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from catalog.models import Brand, Category, Product
from commerce.models import Order
from users.models import User


class CommerceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Graphics Cards", slug="graphics-cards")
        self.brand = Brand.objects.create(name="NexCore")
        self.product = Product.objects.create(
            name="NexCore RTX 5070",
            description="GPU",
            price=599.99,
            stock_quantity=3,
            category=self.category,
            brand=self.brand,
            rating=4.8,
            weight_kg=1.2,
            weight_lb=2.65,
            length_cm=30,
            width_cm=12,
            height_cm=4,
            length_in=11.8,
            width_in=4.7,
            height_in=1.6,
        )
        self.alt_product = Product.objects.create(
            name="NexCore RTX 4060",
            description="GPU",
            price=299.99,
            stock_quantity=9,
            category=self.category,
            brand=self.brand,
            rating=4.2,
            weight_kg=0.9,
            weight_lb=1.98,
            length_cm=24,
            width_cm=11,
            height_cm=3,
            length_in=9.4,
            width_in=4.3,
            height_in=1.2,
        )

    def test_guest_cart_add_update_remove_and_totals(self):
        add = self.client.post(
            "/api/commerce/cart/items/",
            {"product_id": self.product.id, "quantity": 2},
            format="json",
        )
        self.assertEqual(add.status_code, 201)
        token = add.data["guest_cart_token"]
        self.assertTrue(token)
        self.assertEqual(add.data["item_count"], 1)

        item_id = add.data["items"][0]["id"]
        update = self.client.patch(
            f"/api/commerce/cart/items/{item_id}/",
            {"quantity": 1},
            format="json",
            HTTP_X_GUEST_CART_TOKEN=token,
        )
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.data["items"][0]["quantity"], 1)

        remove = self.client.delete(
            f"/api/commerce/cart/items/{item_id}/",
            HTTP_X_GUEST_CART_TOKEN=token,
        )
        self.assertEqual(remove.status_code, 200)
        self.assertEqual(remove.data["item_count"], 0)

    def test_cart_out_of_stock_handled(self):
        response = self.client.post(
            "/api/commerce/cart/items/",
            {"product_id": self.product.id, "quantity": 99},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_checkout_guest_success_flow(self):
        add = self.client.post(
            "/api/commerce/cart/items/",
            {"product_id": self.product.id, "quantity": 1},
            format="json",
        )
        token = add.data["guest_cart_token"]

        payload = {
            "full_name": "Guest Buyer",
            "email": "guest@example.com",
            "phone": "+358401234567",
            "shipping_address": {
                "line1": "Main street 1",
                "city": "Helsinki",
                "state": "Uusimaa",
                "postal_code": "00100",
                "country": "FI",
            },
            "shipping_option": "standard",
            "payment_method": "stripe_sandbox",
            "card_number": "4242424242424242",
            "expiry_month": 12,
            "expiry_year": timezone.now().year + 1,
            "cvv": "123",
        }
        checkout = self.client.post(
            "/api/commerce/checkout/place-order/",
            payload,
            format="json",
            HTTP_X_GUEST_CART_TOKEN=token,
        )
        self.assertEqual(checkout.status_code, 201)
        self.assertEqual(checkout.data["payment"]["status"], "success")
        self.assertEqual(checkout.data["order"]["status"], Order.STATUS_PAYMENT_SUCCESSFUL)

    def test_checkout_guest_failure_scenarios(self):
        add = self.client.post(
            "/api/commerce/cart/items/",
            {"product_id": self.product.id, "quantity": 1},
            format="json",
        )
        token = add.data["guest_cart_token"]

        payload = {
            "full_name": "Guest Buyer",
            "email": "guest@example.com",
            "phone": "+358401234567",
            "shipping_address": {
                "line1": "Main street 1",
                "city": "Helsinki",
                "state": "Uusimaa",
                "postal_code": "00100",
                "country": "FI",
            },
            "shipping_option": "standard",
            "payment_method": "stripe_sandbox",
            "card_number": "4000000000009995",
            "expiry_month": 12,
            "expiry_year": timezone.now().year + 1,
            "cvv": "123",
        }
        checkout = self.client.post(
            "/api/commerce/checkout/place-order/",
            payload,
            format="json",
            HTTP_X_GUEST_CART_TOKEN=token,
        )
        self.assertEqual(checkout.status_code, 201)
        self.assertEqual(checkout.data["payment"]["status"], "failure")
        self.assertEqual(checkout.data["payment"]["failure_code"], "insufficient_funds")

    def test_checkout_tokenized_payment_flow(self):
        add = self.client.post(
            "/api/commerce/cart/items/",
            {"product_id": self.product.id, "quantity": 1},
            format="json",
        )
        token = add.data["guest_cart_token"]

        payload = {
            "full_name": "Guest Buyer",
            "email": "guest@example.com",
            "phone": "+358401234567",
            "shipping_address": {
                "line1": "Main street 1",
                "city": "Helsinki",
                "state": "Uusimaa",
                "postal_code": "00100",
                "country": "FI",
            },
            "shipping_option": "standard",
            "payment_method": "stripe_sandbox",
            "payment_token": "pm_test_token_123",
        }
        checkout = self.client.post(
            "/api/commerce/checkout/place-order/",
            payload,
            format="json",
            HTTP_X_GUEST_CART_TOKEN=token,
        )
        self.assertEqual(checkout.status_code, 201)
        self.assertEqual(checkout.data["payment"]["status"], "success")

    def test_checkout_prefill_for_logged_user(self):
        user = User.objects.create_user(
            email="buyer@example.com",
            password="StrongPass123!",
            full_name="Buyer Name",
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/commerce/checkout/prefill/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "buyer@example.com")

    def test_order_filtering_by_status_and_date(self):
        user = User.objects.create_user(
            email="orders@example.com",
            password="StrongPass123!",
            full_name="Order User",
        )
        old = Order.objects.create(
            user=user,
            status=Order.STATUS_PAYMENT_FAILED,
            payment_method="stripe_sandbox",
            shipping_option=Order.SHIPPING_STANDARD,
            subtotal=10,
            total=17.9,
            shipping_cost=7.9,
        )
        Order.objects.filter(id=old.id).update(created_at=timezone.now() - timedelta(days=15))
        Order.objects.create(
            user=user,
            status=Order.STATUS_PAYMENT_SUCCESSFUL,
            payment_method="stripe_sandbox",
            shipping_option=Order.SHIPPING_STANDARD,
            subtotal=10,
            total=17.9,
            shipping_cost=7.9,
        )

        self.client.force_authenticate(user=user)
        by_status = self.client.get(f"/api/commerce/orders/?status={Order.STATUS_PAYMENT_SUCCESSFUL}")
        self.assertEqual(by_status.status_code, 200)
        self.assertEqual(len(by_status.data), 1)

        by_date = self.client.get("/api/commerce/orders/?date_from=2100-01-01")
        self.assertEqual(by_date.status_code, 200)
        self.assertEqual(len(by_date.data), 0)

    def test_cancel_unprocessed_order_restocks_inventory(self):
        user = User.objects.create_user(
            email="cancel@example.com",
            password="StrongPass123!",
            full_name="Cancel User",
        )
        order = Order.objects.create(
            user=user,
            status=Order.STATUS_PAYMENT_SUCCESSFUL,
            payment_method="stripe_sandbox",
            shipping_option=Order.SHIPPING_STANDARD,
            subtotal=599.99,
            total=607.89,
            shipping_cost=7.90,
        )
        order.items.create(
            product=self.product,
            product_name=self.product.name,
            quantity=1,
            unit_price=599.99,
            line_total=599.99,
        )
        self.product.stock_quantity = 1
        self.product.save(update_fields=["stock_quantity"])

        self.client.force_authenticate(user=user)
        response = self.client.post(f"/api/commerce/orders/{order.id}/cancel/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 2)

    def test_inventory_oversell_prevention(self):
        self.product.stock_quantity = 1
        self.product.save(update_fields=["stock_quantity"])

        add_a = self.client.post(
            "/api/commerce/cart/items/",
            {"product_id": self.product.id, "quantity": 1},
            format="json",
        )
        guest_a = add_a.data["guest_cart_token"]

        client_b = APIClient()
        add_b = client_b.post(
            "/api/commerce/cart/items/",
            {"product_id": self.product.id, "quantity": 1},
            format="json",
        )
        guest_b = add_b.data["guest_cart_token"]

        payload = {
            "full_name": "Buyer One",
            "email": "one@example.com",
            "phone": "+358401111111",
            "shipping_address": {
                "line1": "Street 1",
                "city": "Helsinki",
                "state": "Uusimaa",
                "postal_code": "00100",
                "country": "FI",
            },
            "shipping_option": "standard",
            "payment_method": "stripe_sandbox",
            "card_number": "4242424242424242",
            "expiry_month": 12,
            "expiry_year": timezone.now().year + 1,
            "cvv": "123",
        }
        ok = self.client.post(
            "/api/commerce/checkout/place-order/",
            payload,
            format="json",
            HTTP_X_GUEST_CART_TOKEN=guest_a,
        )
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(ok.data["payment"]["status"], "success")

        fail = client_b.post(
            "/api/commerce/checkout/place-order/",
            payload | {"email": "two@example.com"},
            format="json",
            HTTP_X_GUEST_CART_TOKEN=guest_b,
        )
        self.assertEqual(fail.status_code, 400)
        self.assertIn("Out of stock", fail.data["detail"])
