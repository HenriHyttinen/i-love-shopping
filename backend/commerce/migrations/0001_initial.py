# Generated manually for commerce app bootstrap.

import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("catalog", "0002_future_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Cart",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("guest_token", models.CharField(blank=True, max_length=64, null=True, unique=True)),
                ("currency", models.CharField(default="USD", max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="cart", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("guest_email", models.EmailField(blank=True, max_length=254)),
                ("guest_name", models.CharField(blank=True, max_length=120)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending_payment", "Pending Payment"),
                            ("payment_successful", "Payment Successful"),
                            ("payment_failed", "Payment Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending_payment",
                        max_length=32,
                    ),
                ),
                ("is_processed", models.BooleanField(default=False)),
                ("payment_method", models.CharField(max_length=40)),
                (
                    "shipping_option",
                    models.CharField(choices=[("standard", "Standard"), ("express", "Express")], max_length=20),
                ),
                ("shipping_cost", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10)),
                ("subtotal", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("total", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("encrypted_shipping_address", models.TextField(blank=True)),
                ("encrypted_order_details", models.TextField(blank=True)),
                ("tracking_code", models.CharField(blank=True, max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="orders", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="CartItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("cart", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="commerce.cart")),
                (
                    "product",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cart_items", to="catalog.product"),
                ),
            ],
            options={"unique_together": {("cart", "product")}},
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_name", models.CharField(max_length=220)),
                ("quantity", models.PositiveIntegerField()),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("line_total", models.DecimalField(decimal_places=2, max_digits=12)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="commerce.order")),
                (
                    "product",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="order_items", to="catalog.product"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="OrderStatusEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(max_length=32)),
                ("note", models.CharField(blank=True, max_length=240)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="status_events", to="commerce.order")),
            ],
            options={"ordering": ("created_at",)},
        ),
        migrations.CreateModel(
            name="PaymentTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(choices=[("pending", "Pending"), ("success", "Success"), ("failure", "Failure")], default="pending", max_length=20),
                ),
                ("provider", models.CharField(max_length=40)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("external_reference", models.CharField(blank=True, max_length=80)),
                ("failure_code", models.CharField(blank=True, max_length=60)),
                ("encrypted_provider_payload", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "order",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="payment_transaction", to="commerce.order"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PaymentStatusMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(max_length=20)),
                ("payload", models.TextField(blank=True)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("dead_lettered", models.BooleanField(default=False)),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payment_messages", to="commerce.order")),
                (
                    "transaction",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="commerce.paymenttransaction"),
                ),
            ],
            options={"ordering": ("created_at",)},
        ),
    ]
