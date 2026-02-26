import re

from rest_framework import serializers

from .address_validation import validate_shipping_address_accuracy
from .crypto import decrypt_json
from .models import DeliveryOption, Order, RefundRequest
from .services import get_shipping_cost


PHONE_RE = re.compile(r"^[+0-9()\-\s]{7,20}$")
POSTAL_RE = re.compile(r"^[A-Za-z0-9\-\s]{3,12}$")
ADDRESS_FIELD_LABELS = {
    "line1": "Address line 1",
    "city": "City",
    "state": "State",
    "postal_code": "Postal code",
    "country": "Country",
}


def _friendly_address_error(detail: str) -> str:
    text = (detail or "").strip().lower()
    if "service unavailable" in text:
        return "Address validation is temporarily unavailable. Please try again in a moment."
    if "line should include a building number" in text or "line is not valid" in text:
        return "Address line 1 looks invalid. Include street name and building number."
    if "state must be a valid state code or name" in text:
        return "State is invalid for the selected country."
    if "must be zip format" in text:
        return "Postal code format is invalid for the selected country."
    if (
        "confidence is too low" in text
        or "does not match" in text
        or "could not be verified" in text
        or "could not verify" in text
    ):
        return "Shipping address doesn't match the city/state/postal code. Please check the address details."
    return detail


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
    shipping_option = serializers.CharField(required=True)
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

    def validate_shipping_option(self, value):
        selected = (value or "").strip()
        if not selected or get_shipping_cost(selected) is None:
            raise serializers.ValidationError("Invalid shipping option.")
        return selected

    def validate_shipping_address(self, value):
        required_fields = ["line1", "city", "postal_code", "country"]
        if _country_requires_state(str(value.get("country", ""))):
            required_fields.append("state")
        missing = [field for field in required_fields if not str(value.get(field, "")).strip()]
        if missing:
            labels = [ADDRESS_FIELD_LABELS.get(field, field) for field in missing]
            raise serializers.ValidationError(f"Missing required fields: {', '.join(labels)}")

        postal_code = str(value.get("postal_code", "")).strip()
        if not POSTAL_RE.match(postal_code):
            raise serializers.ValidationError("Postal code format is invalid.")

        accuracy = validate_shipping_address_accuracy(value)
        if not accuracy.ok:
            raise serializers.ValidationError(_friendly_address_error(accuracy.detail))
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


class DeliveryOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryOption
        fields = ("id", "code", "label", "cost", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class RefundRequestSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.SerializerMethodField()

    class Meta:
        model = RefundRequest
        fields = (
            "id",
            "order",
            "requested_by",
            "requested_by_email",
            "reason",
            "status",
            "note",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "requested_by", "requested_by_email", "created_at", "updated_at")

    def get_requested_by_email(self, obj):
        return obj.requested_by.email if obj.requested_by else ""


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            Order.STATUS_PENDING_PAYMENT,
            Order.STATUS_PAYMENT_SUCCESSFUL,
            Order.STATUS_PAYMENT_FAILED,
            Order.STATUS_CANCELLED,
        ]
    )
    note = serializers.CharField(required=False, allow_blank=True, max_length=240)


class RefundStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[RefundRequest.STATUS_PENDING, RefundRequest.STATUS_APPROVED, RefundRequest.STATUS_REJECTED])
    note = serializers.CharField(required=False, allow_blank=True, max_length=240)
