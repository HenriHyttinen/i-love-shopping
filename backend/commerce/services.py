import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from catalog.models import Product

from .crypto import decrypt_json, encrypt_json
from .models import (
    Cart,
    CartItem,
    Order,
    OrderItem,
    OrderStatusEvent,
    PaymentStatusMessage,
    PaymentTransaction,
)


SHIPPING_COSTS = {
    Order.SHIPPING_STANDARD: Decimal("7.90"),
    Order.SHIPPING_EXPRESS: Decimal("18.90"),
}


@dataclass
class PaymentResult:
    status: str
    failure_code: str = ""
    message: str = ""


def get_or_create_cart(user=None, guest_token: str = "") -> Cart:
    if user and user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=user)
        return cart
    if not guest_token:
        guest_token = Cart.generate_guest_token()
    cart, _ = Cart.objects.get_or_create(guest_token=guest_token)
    return cart


def cart_totals(cart: Cart) -> dict:
    subtotal = Decimal("0.00")
    items = []
    for item in cart.items.select_related("product", "product__brand", "product__category", "product__images"):
        line_total = item.unit_price * item.quantity
        subtotal += line_total
        first_image = item.product.images.first()
        items.append(
            {
                "id": item.id,
                "product_id": item.product_id,
                "name": item.product.name,
                "price": str(item.unit_price),
                "quantity": item.quantity,
                "line_total": str(line_total),
                "thumbnail": first_image.image.url if first_image else "",
                "stock_quantity": item.product.stock_quantity,
            }
        )
    return {
        "cart_id": cart.id,
        "currency": cart.currency,
        "subtotal": str(subtotal),
        "item_count": len(items),
        "items": items,
    }


def recommended_products(cart: Cart, limit: int = 4) -> list:
    item_product_ids = list(cart.items.values_list("product_id", flat=True))
    if not item_product_ids:
        return []
    brand_ids = list(Product.objects.filter(id__in=item_product_ids).values_list("brand_id", flat=True))
    category_ids = list(Product.objects.filter(id__in=item_product_ids).values_list("category_id", flat=True))
    products = (
        Product.objects.filter(is_active=True, stock_quantity__gt=0)
        .exclude(id__in=item_product_ids)
        .filter(Q(brand_id__in=brand_ids) | Q(category_id__in=category_ids))
        .distinct()[:limit]
    )
    return [
        {
            "id": product.id,
            "name": product.name,
            "price": str(product.price),
            "stock_quantity": product.stock_quantity,
        }
        for product in products
    ]


def simulate_payment(
    payment_provider: str,
    card_number: str = "",
    expiry_month: int | None = None,
    expiry_year: int | None = None,
    cvv: str = "",
    payment_token: str = "",
) -> PaymentResult:
    if payment_provider not in {"stripe_sandbox", "paypal_sandbox"}:
        return PaymentResult(status=PaymentTransaction.STATUS_FAILURE, failure_code="unsupported_provider", message="Unsupported payment provider.")
    if payment_token:
        token_failure_map = {
            "tok_fail_insufficient_funds": ("insufficient_funds", "Card has insufficient funds."),
            "tok_fail_invalid_card": ("invalid_card_number", "Card number was declined by provider."),
            "tok_fail_expired_card": ("expired_card", "Card has expired."),
            "tok_fail_gateway_timeout": ("gateway_timeout", "Payment gateway timeout. Please retry."),
        }
        if payment_token in token_failure_map:
            failure_code, message = token_failure_map[payment_token]
            return PaymentResult(
                status=PaymentTransaction.STATUS_FAILURE,
                failure_code=failure_code,
                message=message,
            )
        return PaymentResult(status=PaymentTransaction.STATUS_SUCCESS)

    if len(card_number) < 12 or not card_number.isdigit():
        return PaymentResult(
            status=PaymentTransaction.STATUS_FAILURE,
            failure_code="invalid_card_number",
            message="Invalid card number.",
        )
    if len(cvv) not in {3, 4} or not cvv.isdigit():
        return PaymentResult(
            status=PaymentTransaction.STATUS_FAILURE,
            failure_code="invalid_cvv",
            message="Invalid CVV.",
        )

    if expiry_month is None or expiry_year is None:
        return PaymentResult(
            status=PaymentTransaction.STATUS_FAILURE,
            failure_code="invalid_expiry",
            message="Expiry date is required.",
        )
    now = datetime.utcnow()
    if expiry_year < now.year or (expiry_year == now.year and expiry_month < now.month):
        return PaymentResult(
            status=PaymentTransaction.STATUS_FAILURE,
            failure_code="expired_card",
            message="Card has expired.",
        )

    code_map = {
        "4000000000009995": ("insufficient_funds", "Card has insufficient funds."),
        "4000000000000002": ("invalid_card_number", "Card number was declined by provider."),
        "4000000000000069": ("expired_card", "Card has expired."),
        "4000000000000127": ("gateway_timeout", "Payment gateway timeout. Please retry."),
    }
    if card_number in code_map:
        failure_code, message = code_map[card_number]
        return PaymentResult(status=PaymentTransaction.STATUS_FAILURE, failure_code=failure_code, message=message)

    return PaymentResult(status=PaymentTransaction.STATUS_SUCCESS)


def publish_payment_message(
    order: Order,
    status: str,
    transaction: PaymentTransaction | None = None,
    payload: dict | None = None,
):
    PaymentStatusMessage.objects.create(
        order=order,
        transaction=transaction,
        status=status,
        payload=encrypt_json(payload or {}),
    )


def consume_payment_messages(order_id: int | None = None):
    query = PaymentStatusMessage.objects.select_for_update().filter(consumed_at__isnull=True, dead_lettered=False)
    if order_id:
        query = query.filter(order_id=order_id)

    for msg in query.order_by("created_at"):
        msg.attempts += 1
        msg.save(update_fields=["attempts"])

        order = msg.order
        payload = decrypt_json(msg.payload)

        if msg.status == PaymentStatusMessage.STATUS_PENDING:
            order.status = Order.STATUS_PENDING_PAYMENT
            note = "Payment initiated"
        elif msg.status == PaymentStatusMessage.STATUS_SUCCESS:
            order.status = Order.STATUS_PAYMENT_SUCCESSFUL
            note = "Payment successful"
            if order.user and order.user.email:
                send_mail(
                    "Your order payment succeeded",
                    f"Order #{order.id} has been paid successfully.",
                    None,
                    [order.user.email],
                    fail_silently=True,
                )
            elif order.guest_email:
                send_mail(
                    "Your order payment succeeded",
                    f"Order #{order.id} has been paid successfully.",
                    None,
                    [order.guest_email],
                    fail_silently=True,
                )
        else:
            order.status = Order.STATUS_PAYMENT_FAILED
            note = payload.get("message", "Payment failed")
            _restore_inventory(order)
            if order.user and order.user.email:
                send_mail(
                    "Your order payment failed",
                    f"Order #{order.id} payment failed: {note}",
                    None,
                    [order.user.email],
                    fail_silently=True,
                )
            elif order.guest_email:
                send_mail(
                    "Your order payment failed",
                    f"Order #{order.id} payment failed: {note}",
                    None,
                    [order.guest_email],
                    fail_silently=True,
                )

        order.save(update_fields=["status", "updated_at"])
        OrderStatusEvent.objects.create(order=order, status=order.status, note=note)
        msg.consumed_at = timezone.now()
        msg.save(update_fields=["consumed_at"])


def _restore_inventory(order: Order):
    for item in order.items.select_related("product"):
        Product.objects.filter(id=item.product_id).update(stock_quantity=F("stock_quantity") + item.quantity)


@transaction.atomic
def place_order_from_cart(
    cart: Cart,
    customer_payload: dict,
    payment_payload: dict,
    shipping_option: str,
    payment_method: str,
    user=None,
) -> tuple[Order, PaymentTransaction]:
    items = list(cart.items.select_related("product"))
    if not items:
        raise ValueError("Cart is empty.")

    product_map = {
        p.id: p
        for p in Product.objects.select_for_update().filter(id__in=[item.product_id for item in items])
    }

    subtotal = Decimal("0.00")
    for item in items:
        product = product_map[item.product_id]
        if product.stock_quantity < item.quantity:
            raise ValueError(f"Out of stock for {product.name}.")
        subtotal += item.unit_price * item.quantity

    shipping_cost = SHIPPING_COSTS.get(shipping_option)
    if shipping_cost is None:
        raise ValueError("Invalid shipping option.")

    order = Order.objects.create(
        user=user if user and user.is_authenticated else None,
        guest_email=customer_payload.get("email", ""),
        guest_name=customer_payload.get("full_name", ""),
        status=Order.STATUS_PENDING_PAYMENT,
        payment_method=payment_method,
        shipping_option=shipping_option,
        shipping_cost=shipping_cost,
        subtotal=subtotal,
        total=subtotal + shipping_cost,
        encrypted_shipping_address=encrypt_json(customer_payload.get("shipping_address", {})),
        encrypted_order_details=encrypt_json(
            {
                "email": customer_payload.get("email", ""),
                "phone": customer_payload.get("phone", ""),
                "placed_from": "authenticated" if user and user.is_authenticated else "guest",
            }
        ),
        tracking_code=f"TRK-{uuid.uuid4().hex[:10].upper()}",
    )

    for item in items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            product_name=item.product.name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.unit_price * item.quantity,
        )
        Product.objects.filter(id=item.product_id).update(stock_quantity=F("stock_quantity") - item.quantity)

    transaction_obj = PaymentTransaction.objects.create(
        order=order,
        provider=payment_method,
        amount=order.total,
        status=PaymentTransaction.STATUS_PENDING,
        external_reference=f"txn_{uuid.uuid4().hex[:16]}",
        encrypted_provider_payload=encrypt_json(
            {
                "provider": payment_method,
                "payment_token": payment_payload.get("payment_token", ""),
                "card_last4": payment_payload.get("card_number", "")[-4:],
                "expiry_month": payment_payload.get("expiry_month"),
                "expiry_year": payment_payload.get("expiry_year"),
            }
        ),
    )
    publish_payment_message(order=order, status=PaymentStatusMessage.STATUS_PENDING, transaction=transaction_obj)

    result = simulate_payment(
        payment_provider=payment_method,
        card_number=payment_payload.get("card_number", ""),
        expiry_month=int(payment_payload["expiry_month"]) if payment_payload.get("expiry_month") else None,
        expiry_year=int(payment_payload["expiry_year"]) if payment_payload.get("expiry_year") else None,
        cvv=payment_payload.get("cvv", ""),
        payment_token=payment_payload.get("payment_token", ""),
    )
    if result.status == PaymentTransaction.STATUS_SUCCESS:
        transaction_obj.status = PaymentTransaction.STATUS_SUCCESS
        transaction_obj.failure_code = ""
        transaction_obj.save(update_fields=["status", "failure_code", "updated_at"])
        publish_payment_message(order=order, status=PaymentStatusMessage.STATUS_SUCCESS, transaction=transaction_obj)
    else:
        transaction_obj.status = PaymentTransaction.STATUS_FAILURE
        transaction_obj.failure_code = result.failure_code
        transaction_obj.save(update_fields=["status", "failure_code", "updated_at"])
        publish_payment_message(
            order=order,
            status=PaymentStatusMessage.STATUS_FAILURE,
            transaction=transaction_obj,
            payload={"failure_code": result.failure_code, "message": result.message},
        )

    consume_payment_messages(order_id=order.id)

    cart.items.all().delete()
    return order, transaction_obj
