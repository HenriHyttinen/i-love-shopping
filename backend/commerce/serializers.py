import re

from django.utils import timezone
from rest_framework import serializers

from .crypto import decrypt_json
from .models import Order


PHONE_RE = re.compile(r"^[+0-9()\-\s]{7,20}$")
POSTAL_RE = re.compile(r"^[A-Za-z0-9\-\s]{3,12}$")


class CartItemMutationSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(min_value=1, max_value=99, required=True)


class CartItemUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0, max_value=99, required=True)


class CheckoutSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=120, required=True)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(max_length=20, required=True)
    shipping_address = serializers.DictField(required=True)
    shipping_option = serializers.ChoiceField(choices=[Order.SHIPPING_STANDARD, Order.SHIPPING_EXPRESS])
    payment_method = serializers.ChoiceField(choices=["stripe_sandbox", "paypal_sandbox"])
    card_number = serializers.CharField(required=True)
    expiry_month = serializers.IntegerField(min_value=1, max_value=12, required=True)
    expiry_year = serializers.IntegerField(min_value=2000, required=True)
    cvv = serializers.CharField(min_length=3, max_length=4, required=True)

    def validate_phone(self, value):
        if not PHONE_RE.match(value):
            raise serializers.ValidationError("Invalid phone format.")
        return value

    def validate_card_number(self, value):
        if not value.isdigit() or len(value) < 12 or len(value) > 19:
            raise serializers.ValidationError("Card number must be 12-19 digits.")
        return value

    def validate_cvv(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("CVV must contain digits only.")
        return value

    def validate_expiry_year(self, value):
        if value > timezone.now().year + 30:
            raise serializers.ValidationError("Invalid expiry year.")
        return value

    def validate_shipping_address(self, value):
        required_fields = ["line1", "city", "state", "postal_code", "country"]
        missing = [field for field in required_fields if not str(value.get(field, "")).strip()]
        if missing:
            raise serializers.ValidationError(f"Missing required fields: {', '.join(missing)}")

        postal_code = str(value.get("postal_code", "")).strip()
        if not POSTAL_RE.match(postal_code):
            raise serializers.ValidationError("Invalid address format for postal_code.")
        return value


class OrderSerializer(serializers.ModelSerializer):
    status_updates = serializers.SerializerMethodField()
    shipping_address = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id",
            "status",
            "is_processed",
            "payment_method",
            "shipping_option",
            "shipping_cost",
            "subtotal",
            "total",
            "tracking_code",
            "shipping_address",
            "created_at",
            "updated_at",
            "status_updates",
        )

    def get_status_updates(self, obj):
        return [
            {
                "status": event.status,
                "note": event.note,
                "created_at": event.created_at,
            }
            for event in obj.status_events.all()
        ]

    def get_shipping_address(self, obj):
        return decrypt_json(obj.encrypted_shipping_address)
