import re

from rest_framework import serializers

from .address_validation import validate_shipping_address_accuracy
from .crypto import decrypt_json
from .models import Order


PHONE_RE = re.compile(r"^[+0-9()\-\s]{7,20}$")
POSTAL_RE = re.compile(r"^[A-Za-z0-9\-\s]{3,12}$")


def _country_requires_state(country: str) -> bool:
    normalized = (country or "").strip().lower()
    return normalized in {
        "us",
        "usa",
        "united states",
        "united states of america",
        "fi",
        "finland",
        "suomi",
        "ca",
        "canada",
        "au",
        "australia",
    }


class CartItemMutationSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1, required=True)
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
    payment_token = serializers.CharField(required=True, allow_blank=False)

    def validate_phone(self, value):
        if not PHONE_RE.match(value):
            raise serializers.ValidationError("Invalid phone format.")
        return value

    def validate_payment_token(self, value):
        token = (value or "").strip()
        if len(token) < 8:
            raise serializers.ValidationError("Invalid payment token.")
        if not (token.startswith("pm_") or token.startswith("tok_")):
            raise serializers.ValidationError("Unsupported payment token format.")
        return token

    def validate_shipping_address(self, value):
        required_fields = ["line1", "city", "postal_code", "country"]
        if _country_requires_state(str(value.get("country", ""))):
            required_fields.append("state")
        missing = [field for field in required_fields if not str(value.get(field, "")).strip()]
        if missing:
            raise serializers.ValidationError(f"Missing required fields: {', '.join(missing)}")

        postal_code = str(value.get("postal_code", "")).strip()
        if not POSTAL_RE.match(postal_code):
            raise serializers.ValidationError("Invalid address format for postal_code.")

        accuracy = validate_shipping_address_accuracy(value)
        if not accuracy.ok:
            raise serializers.ValidationError(accuracy.detail)
        return value

    def validate(self, attrs):
        if attrs["payment_method"] == "paypal_sandbox" and not attrs["payment_token"].startswith("tok_"):
            raise serializers.ValidationError({"payment_token": "PayPal sandbox requires a tok_* payment token."})
        return attrs


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
