from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from catalog.models import Brand, Category, Product
from commerce.models import Order, PaymentTransaction
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
        self.assertIn("recommended_products", add.data)
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

    def test_recommended_products_fallback_when_no_related_matches(self):
        unique_category = Category.objects.create(name="Cases", slug="cases")
        unique_brand = Brand.objects.create(name="CaseBrand")
        unique_product = Product.objects.create(
            name="CaseBrand Tower 1",
            description="Unique category+brand item",
            price=129.99,
            stock_quantity=5,
            category=unique_category,
            brand=unique_brand,
            rating=4.1,
            weight_kg=6.0,
            weight_lb=13.2,
            length_cm=45,
            width_cm=22,
            height_cm=47,
            length_in=17.7,
            width_in=8.7,
            height_in=18.5,
        )
        add = self.client.post(
            "/api/commerce/cart/items/",
            {"product_id": unique_product.id, "quantity": 1},
            format="json",
        )
        token = add.data["guest_cart_token"]
        cart = self.client.get("/api/commerce/cart/", HTTP_X_GUEST_CART_TOKEN=token)
        self.assertEqual(cart.status_code, 200)
        self.assertGreaterEqual(len(cart.data.get("recommended_products", [])), 1)

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
            "payment_token": "tok_success",
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
        self.assertIn("notification", checkout.data)
        self.assertEqual(checkout.data["notification"]["channel"], "email")
        self.assertIn(checkout.data["notification"]["status"], {"sent", "failed", "skipped", "queued"})

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
            "payment_token": "tok_fail_insufficient_funds",
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
        self.assertIn("notification", checkout.data)
        self.assertEqual(checkout.data["notification"]["channel"], "email")
        self.assertIn(checkout.data["notification"]["status"], {"sent", "failed", "skipped", "queued"})

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

    def test_logged_in_checkout_flow_uses_persistent_cart(self):
        user = User.objects.create_user(
            email="member@example.com",
            password="StrongPass123!",
            full_name="Member Buyer",
        )
        self.client.force_authenticate(user=user)
        add = self.client.post(
            "/api/commerce/cart/items/",
            {"product_id": self.product.id, "quantity": 1},
            format="json",
        )
        self.assertEqual(add.status_code, 201)
        self.assertEqual(add.data["guest_cart_token"], "")

        checkout = self.client.post(
            "/api/commerce/checkout/place-order/",
            {
                "full_name": "Member Buyer",
                "email": "member@example.com",
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
                "payment_token": "tok_success",
            },
            format="json",
        )
        self.assertEqual(checkout.status_code, 201)
        self.assertEqual(checkout.data["order"]["status"], Order.STATUS_PAYMENT_SUCCESSFUL)
        self.assertEqual(Order.objects.filter(user=user).count(), 1)

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
            "payment_token": "tok_success",
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

    def test_checkout_order_totals_include_shipping_cost(self):
        add = self.client.post(
            "/api/commerce/cart/items/",
            {"product_id": self.product.id, "quantity": 2},
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
            "shipping_option": "express",
            "payment_method": "stripe_sandbox",
            "payment_token": "tok_success",
        }
        checkout = self.client.post(
            "/api/commerce/checkout/place-order/",
            payload,
            format="json",
            HTTP_X_GUEST_CART_TOKEN=token,
        )
        self.assertEqual(checkout.status_code, 201)
        order = checkout.data["order"]
        self.assertEqual(str(order["subtotal"]), "1199.98")
        self.assertEqual(str(order["shipping_cost"]), "18.90")
        self.assertEqual(str(order["total"]), "1218.88")

    def test_checkout_rejects_missing_payment_token(self):
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
        }
        checkout = self.client.post(
            "/api/commerce/checkout/place-order/",
            payload,
            format="json",
            HTTP_X_GUEST_CART_TOKEN=token,
        )
        self.assertEqual(checkout.status_code, 400)
        self.assertIn("payment_token", checkout.data)

    def test_checkout_failure_tokens_cover_required_scenarios(self):
        failure_cases = [
            ("tok_fail_insufficient_funds", "insufficient_funds"),
            ("tok_fail_invalid_card", "invalid_card_number"),
            ("tok_fail_expired_card", "expired_card"),
            ("tok_fail_gateway_timeout", "gateway_timeout"),
        ]
        for payment_token, expected_code in failure_cases:
            add = self.client.post(
                "/api/commerce/cart/items/",
                {"product_id": self.product.id, "quantity": 1},
                format="json",
            )
            guest_token = add.data["guest_cart_token"]
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
                "payment_token": payment_token,
            }
            checkout = self.client.post(
                "/api/commerce/checkout/place-order/",
                payload,
                format="json",
                HTTP_X_GUEST_CART_TOKEN=guest_token,
            )
            self.assertEqual(checkout.status_code, 201)
            self.assertEqual(checkout.data["payment"]["status"], "failure")
            self.assertEqual(checkout.data["payment"]["failure_code"], expected_code)

    def test_payment_callback_endpoint_updates_order_status(self):
        order = Order.objects.create(
            status=Order.STATUS_PENDING_PAYMENT,
            payment_method="stripe_sandbox",
            shipping_option=Order.SHIPPING_STANDARD,
            subtotal=10,
            total=17.9,
            shipping_cost=7.9,
            guest_email="guest@example.com",
            guest_name="Guest Buyer",
        )
        tx = PaymentTransaction.objects.create(
            order=order,
            provider="stripe_sandbox",
            status=PaymentTransaction.STATUS_PENDING,
            amount=order.total,
            external_reference="txn_callback_status_update_1",
        )

        callback = self.client.post(
            "/api/commerce/payments/callback/",
            {
                "external_reference": tx.external_reference,
                "status": "failure",
                "failure_code": "gateway_timeout",
                "message": "Timed out at provider edge",
            },
            format="json",
        )
        self.assertEqual(callback.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PAYMENT_FAILED)
        tx.refresh_from_db()
        self.assertEqual(tx.failure_code, "gateway_timeout")

    @override_settings(PAYMENT_CALLBACK_SECRET="secret-123")
    def test_payment_callback_requires_secret_when_configured(self):
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
            "payment_token": "tok_success",
        }
        checkout = self.client.post(
            "/api/commerce/checkout/place-order/",
            payload,
            format="json",
            HTTP_X_GUEST_CART_TOKEN=token,
        )
        self.assertEqual(checkout.status_code, 201)
        external_reference = checkout.data["payment"]["external_reference"]

        unauthorized = self.client.post(
            "/api/commerce/payments/callback/",
            {
                "external_reference": external_reference,
                "status": "success",
            },
            format="json",
        )
        self.assertEqual(unauthorized.status_code, 403)

        authorized = self.client.post(
            "/api/commerce/payments/callback/",
            {
                "external_reference": external_reference,
                "status": "success",
            },
            format="json",
            HTTP_X_PAYMENT_CALLBACK_SECRET="secret-123",
        )
        self.assertEqual(authorized.status_code, 200)

    def test_payment_callback_rejects_terminal_state_regression(self):
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
            "payment_token": "tok_success",
        }
        checkout = self.client.post(
            "/api/commerce/checkout/place-order/",
            payload,
            format="json",
            HTTP_X_GUEST_CART_TOKEN=token,
        )
        self.assertEqual(checkout.status_code, 201)

        external_reference = checkout.data["payment"]["external_reference"]
        rejected = self.client.post(
            "/api/commerce/payments/callback/",
            {
                "external_reference": external_reference,
                "status": "failure",
                "failure_code": "gateway_timeout",
                "message": "Late failure callback",
            },
            format="json",
        )
        self.assertEqual(rejected.status_code, 409)

    def test_repeated_failure_callback_is_idempotent_for_inventory(self):
        self.product.stock_quantity = 2
        self.product.save(update_fields=["stock_quantity"])

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
            "payment_token": "tok_fail_insufficient_funds",
        }
        checkout = self.client.post(
            "/api/commerce/checkout/place-order/",
            payload,
            format="json",
            HTTP_X_GUEST_CART_TOKEN=token,
        )
        self.assertEqual(checkout.status_code, 201)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 2)

        external_reference = checkout.data["payment"]["external_reference"]
        repeat = self.client.post(
            "/api/commerce/payments/callback/",
            {
                "external_reference": external_reference,
                "status": "failure",
                "failure_code": "insufficient_funds",
                "message": "Duplicate failure callback",
            },
            format="json",
        )
        self.assertEqual(repeat.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 2)

    def test_staff_can_process_order_and_block_cancellation(self):
        buyer = User.objects.create_user(
            email="process-buyer@example.com",
            password="StrongPass123!",
            full_name="Process Buyer",
        )
        staff = User.objects.create_user(
            email="staff@example.com",
            password="StrongPass123!",
            full_name="Staff User",
            is_staff=True,
        )
        order = Order.objects.create(
            user=buyer,
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

        self.client.force_authenticate(user=staff)
        process = self.client.post(f"/api/commerce/orders/{order.id}/process/", {}, format="json")
        self.assertEqual(process.status_code, 200)
        order.refresh_from_db()
        self.assertTrue(order.is_processed)

        self.client.force_authenticate(user=buyer)
        cancel = self.client.post(f"/api/commerce/orders/{order.id}/cancel/", {}, format="json")
        self.assertEqual(cancel.status_code, 400)
        self.assertIn("already processed", cancel.data["detail"])
