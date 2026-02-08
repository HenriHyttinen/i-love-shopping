import secrets
from decimal import Decimal

from django.conf import settings
from django.db import models

from catalog.models import Product


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        null=True,
        blank=True,
    )
    guest_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    currency = models.CharField(max_length=8, default="USD")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @staticmethod
    def generate_guest_token() -> str:
        return secrets.token_hex(24)

    @property
    def subtotal(self) -> Decimal:
        total = Decimal("0.00")
        for item in self.items.select_related("product"):
            total += item.unit_price * item.quantity
        return total

    def __str__(self):
        return f"cart:{self.id}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("cart", "product")

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity


class Order(models.Model):
    STATUS_PENDING_PAYMENT = "pending_payment"
    STATUS_PAYMENT_SUCCESSFUL = "payment_successful"
    STATUS_PAYMENT_FAILED = "payment_failed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING_PAYMENT, "Pending Payment"),
        (STATUS_PAYMENT_SUCCESSFUL, "Payment Successful"),
        (STATUS_PAYMENT_FAILED, "Payment Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    SHIPPING_STANDARD = "standard"
    SHIPPING_EXPRESS = "express"
    SHIPPING_CHOICES = [
        (SHIPPING_STANDARD, "Standard"),
        (SHIPPING_EXPRESS, "Express"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="orders",
        null=True,
        blank=True,
    )
    guest_email = models.EmailField(blank=True)
    guest_name = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PENDING_PAYMENT)
    is_processed = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=40)
    shipping_option = models.CharField(max_length=20, choices=SHIPPING_CHOICES)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    encrypted_shipping_address = models.TextField(blank=True)
    encrypted_order_details = models.TextField(blank=True)
    tracking_code = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    product_name = models.CharField(max_length=220)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)


class PaymentTransaction(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILURE = "failure"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILURE, "Failure"),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment_transaction")
    provider = models.CharField(max_length=40)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    external_reference = models.CharField(max_length=80, blank=True)
    failure_code = models.CharField(max_length=60, blank=True)
    encrypted_provider_payload = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PaymentStatusMessage(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILURE = "failure"

    transaction = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.CASCADE,
        related_name="messages",
        null=True,
        blank=True,
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payment_messages")
    status = models.CharField(max_length=20)
    payload = models.TextField(blank=True)
    attempts = models.PositiveIntegerField(default=0)
    dead_lettered = models.BooleanField(default=False)
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)


class OrderStatusEvent(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_events")
    status = models.CharField(max_length=32)
    note = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
