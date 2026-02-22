import logging
import uuid
from dataclasses import dataclass
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

logger = logging.getLogger(__name__)


ALLOWED_PAYMENT_ORDER_TRANSITIONS = {
    Order.STATUS_PENDING_PAYMENT: {
        Order.STATUS_PENDING_PAYMENT,
        Order.STATUS_PAYMENT_SUCCESSFUL,
        Order.STATUS_PAYMENT_FAILED,
    },
    Order.STATUS_PAYMENT_SUCCESSFUL: {Order.STATUS_PAYMENT_SUCCESSFUL},
    Order.STATUS_PAYMENT_FAILED: {Order.STATUS_PAYMENT_FAILED},
    Order.STATUS_CANCELLED: {Order.STATUS_CANCELLED},
}


@dataclass
class PaymentResult:
    status: str
    failure_code: str = ""
    message: str = ""


def get_or_create_cart(user=None, guest_token: str = "") -> Cart:
    if user and user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=user)
        if guest_token:
            guest_cart = Cart.objects.filter(guest_token=guest_token).prefetch_related("items").first()
            if guest_cart and guest_cart.items.exists():
                for item in guest_cart.items.select_related("product"):
                    merged, created = CartItem.objects.get_or_create(
                        cart=cart,
                        product=item.product,
                        defaults={"quantity": item.quantity, "unit_price": item.unit_price},
                    )
                    if not created:
                        merged.quantity += item.quantity
                        merged.unit_price = item.unit_price
                        merged.save(update_fields=["quantity", "unit_price", "updated_at"])
                guest_cart.delete()
        return cart
    if not guest_token:
        guest_token = Cart.generate_guest_token()
    cart, _ = Cart.objects.get_or_create(guest_token=guest_token)
    return cart


def cart_totals(cart: Cart) -> dict:
    subtotal = Decimal("0.00")
    items = []
    for item in cart.items.select_related("product", "product__brand", "product__category").prefetch_related("product__images"):
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
    in_stock_pool = Product.objects.filter(is_active=True, stock_quantity__gt=0).exclude(id__in=item_product_ids)
    brand_ids = [
        brand_id for brand_id in Product.objects.filter(id__in=item_product_ids).values_list("brand_id", flat=True) if brand_id
    ]
    category_ids = [
        category_id
        for category_id in Product.objects.filter(id__in=item_product_ids).values_list("category_id", flat=True)
        if category_id
    ]

    products = in_stock_pool.filter(Q(brand_id__in=brand_ids) | Q(category_id__in=category_ids)).distinct()[:limit]

    # Fallback so recommendations still render when cart items are unique across brand/category.
    if not products:
        products = in_stock_pool.order_by("-rating", "price")[:limit]

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
    payment_token: str = "",
) -> PaymentResult:
    if payment_provider not in {"stripe_sandbox", "paypal_sandbox"}:
        return PaymentResult(status=PaymentTransaction.STATUS_FAILURE, failure_code="unsupported_provider", message="Unsupported payment provider.")
    if not payment_token:
        return PaymentResult(
            status=PaymentTransaction.STATUS_FAILURE,
            failure_code="invalid_payment_token",
            message="Payment token is required.",
        )

    token_failure_map = {
        "tok_fail_insufficient_funds": ("insufficient_funds", "Card has insufficient funds."),
        "tok_fail_invalid_card": ("invalid_card_number", "Card number was declined by provider."),
        "tok_fail_expired_card": ("expired_card", "Card has expired."),
        "tok_fail_gateway_timeout": ("gateway_timeout", "Payment gateway timeout. Please retry."),
    }
    if payment_token in token_failure_map:
        failure_code, message = token_failure_map[payment_token]
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


def map_message_status_to_order_status(message_status: str) -> str:
    if message_status == PaymentStatusMessage.STATUS_PENDING:
        return Order.STATUS_PENDING_PAYMENT
    if message_status == PaymentStatusMessage.STATUS_SUCCESS:
        return Order.STATUS_PAYMENT_SUCCESSFUL
    return Order.STATUS_PAYMENT_FAILED


def is_allowed_payment_order_transition(current_status: str, target_status: str) -> bool:
    return target_status in ALLOWED_PAYMENT_ORDER_TRANSITIONS.get(current_status, set())


def _notification_recipient(order: Order) -> str:
    if order.user and order.user.email:
        return order.user.email
    return order.guest_email or ""


def _send_payment_notification_email(order: Order, *, success: bool, note: str) -> dict:
    recipient = _notification_recipient(order)
    if not recipient:
        return {
            "channel": "email",
            "recipient": "",
            "status": "skipped",
            "detail": "No email recipient available.",
        }

    if success:
        subject = "Your order payment succeeded"
        body = f"Order #{order.id} has been paid successfully."
    else:
        subject = "Your order payment failed"
        body = f"Order #{order.id} payment failed: {note}"

    try:
        delivered = send_mail(
            subject,
            body,
            None,
            [recipient],
            fail_silently=False,
        )
        if delivered:
            return {
                "channel": "email",
                "recipient": recipient,
                "status": "sent",
                "detail": "Email notification sent.",
            }
        logger.warning("Email backend returned 0 recipients for order=%s recipient=%s", order.id, recipient)
        return {
            "channel": "email",
            "recipient": recipient,
            "status": "failed",
            "detail": "Email backend did not confirm delivery.",
        }
    except Exception as exc:
        logger.exception(
            "Failed to send payment notification email for order=%s recipient=%s error=%s",
            order.id,
            recipient,
            exc.__class__.__name__,
        )
        return {
            "channel": "email",
            "recipient": recipient,
            "status": "failed",
            "detail": "Email delivery failed.",
        }


def consume_payment_messages(order_id: int | None = None):
    max_attempts = 5
    notification_results: dict[int, dict] = {}
    query = PaymentStatusMessage.objects.select_for_update().filter(consumed_at__isnull=True, dead_lettered=False)
    if order_id:
        query = query.filter(order_id=order_id)

    for msg in query.order_by("created_at"):
        try:
            msg.attempts += 1
            msg.save(update_fields=["attempts"])

            order = msg.order
            payload = decrypt_json(msg.payload)
            previous_status = order.status
            target_status = map_message_status_to_order_status(msg.status)

            if not is_allowed_payment_order_transition(previous_status, target_status):
                msg.consumed_at = timezone.now()
                msg.save(update_fields=["consumed_at"])
                OrderStatusEvent.objects.create(
                    order=order,
                    status=previous_status,
                    note=f"Ignored invalid payment transition to {target_status}",
                )
                continue

            if previous_status == target_status:
                msg.consumed_at = timezone.now()
                msg.save(update_fields=["consumed_at"])
                continue

            order.status = target_status
            if msg.status == PaymentStatusMessage.STATUS_PENDING:
                note = "Payment initiated"
            elif msg.status == PaymentStatusMessage.STATUS_SUCCESS:
                note = "Payment successful"
                notification = _send_payment_notification_email(order, success=True, note=note)
                notification_results[order.id] = notification
                if notification.get("status") != "sent":
                    logger.warning(
                        "Payment succeeded but notification failed for order=%s status=%s detail=%s recipient=%s",
                        order.id,
                        notification.get("status", "unknown"),
                        notification.get("detail", ""),
                        notification.get("recipient", ""),
                    )
            else:
                note = payload.get("message", "Payment failed")
                if previous_status != Order.STATUS_PAYMENT_FAILED:
                    _restore_inventory(order)
                notification = _send_payment_notification_email(order, success=False, note=note)
                notification_results[order.id] = notification
                if notification.get("status") != "sent":
                    logger.info(
                        "Payment failed and notification was not sent for order=%s status=%s detail=%s recipient=%s",
                        order.id,
                        notification.get("status", "unknown"),
                        notification.get("detail", ""),
                        notification.get("recipient", ""),
                    )

            order.save(update_fields=["status", "updated_at"])
            OrderStatusEvent.objects.create(order=order, status=order.status, note=note)
            msg.consumed_at = timezone.now()
            msg.save(update_fields=["consumed_at"])
        except Exception:
            if msg.attempts >= max_attempts:
                msg.dead_lettered = True
                msg.save(update_fields=["dead_lettered"])
    return notification_results


def _restore_inventory(order: Order):
    for item in order.items.select_related("product"):
        Product.objects.filter(id=item.product_id).update(stock_quantity=F("stock_quantity") + item.quantity)


def _cart_item_signature(items: list[CartItem]) -> tuple[tuple[int, int, str], ...]:
    return tuple(sorted((item.product_id, item.quantity, str(item.unit_price)) for item in items))


def _order_item_signature(order: Order) -> tuple[tuple[int, int, str], ...]:
    return tuple(sorted((item.product_id, item.quantity, str(item.unit_price)) for item in order.items.all()))


def _find_retryable_failed_order(
    *,
    items: list[CartItem],
    user,
    customer_payload: dict,
    shipping_option: str,
    payment_method: str,
) -> Order | None:
    target_signature = _cart_item_signature(items)
    if not target_signature:
        return None

    queryset = Order.objects.filter(
        status=Order.STATUS_PAYMENT_FAILED,
        is_processed=False,
        shipping_option=shipping_option,
        payment_method=payment_method,
    ).prefetch_related("items")

    if user and user.is_authenticated:
        queryset = queryset.filter(user=user)
    else:
        queryset = queryset.filter(user__isnull=True, guest_email=customer_payload.get("email", ""))

    for candidate in queryset.order_by("-updated_at")[:8]:
        if _order_item_signature(candidate) == target_signature:
            return candidate
    return None


@transaction.atomic
def place_order_from_cart(
    cart: Cart,
    customer_payload: dict,
    payment_payload: dict,
    shipping_option: str,
    payment_method: str,
    user=None,
) -> tuple[Order, PaymentTransaction, dict]:
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

    retry_order = _find_retryable_failed_order(
        items=items,
        user=user,
        customer_payload=customer_payload,
        shipping_option=shipping_option,
        payment_method=payment_method,
    )

    if retry_order:
        order = retry_order
        order.status = Order.STATUS_PENDING_PAYMENT
        order.guest_email = customer_payload.get("email", "")
        order.guest_name = customer_payload.get("full_name", "")
        order.shipping_cost = shipping_cost
        order.subtotal = subtotal
        order.total = subtotal + shipping_cost
        order.encrypted_shipping_address = encrypt_json(customer_payload.get("shipping_address", {}))
        order.encrypted_order_details = encrypt_json(
            {
                "email": customer_payload.get("email", ""),
                "phone": customer_payload.get("phone", ""),
                "placed_from": "authenticated" if user and user.is_authenticated else "guest",
            }
        )
        order.save(
            update_fields=[
                "status",
                "guest_email",
                "guest_name",
                "shipping_cost",
                "subtotal",
                "total",
                "encrypted_shipping_address",
                "encrypted_order_details",
                "updated_at",
            ]
        )
        OrderStatusEvent.objects.create(order=order, status=order.status, note="Payment retry initiated")
    else:
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

    for item in items:
        Product.objects.filter(id=item.product_id).update(stock_quantity=F("stock_quantity") - item.quantity)

    if retry_order and hasattr(order, "payment_transaction"):
        transaction_obj = order.payment_transaction
        transaction_obj.provider = payment_method
        transaction_obj.amount = order.total
        transaction_obj.status = PaymentTransaction.STATUS_PENDING
        transaction_obj.external_reference = f"txn_{uuid.uuid4().hex[:16]}"
        transaction_obj.failure_code = ""
        transaction_obj.encrypted_provider_payload = encrypt_json(
            {
                "provider": payment_method,
                "tokenized": True,
                "payment_token_hint": (payment_payload.get("payment_token", "") or "")[-8:],
            }
        )
        transaction_obj.save(
            update_fields=[
                "provider",
                "amount",
                "status",
                "external_reference",
                "failure_code",
                "encrypted_provider_payload",
                "updated_at",
            ]
        )
    else:
        transaction_obj = PaymentTransaction.objects.create(
            order=order,
            provider=payment_method,
            amount=order.total,
            status=PaymentTransaction.STATUS_PENDING,
            external_reference=f"txn_{uuid.uuid4().hex[:16]}",
            encrypted_provider_payload=encrypt_json(
                {
                    "provider": payment_method,
                    "tokenized": True,
                    "payment_token_hint": (payment_payload.get("payment_token", "") or "")[-8:],
                }
            ),
        )
    publish_payment_message(order=order, status=PaymentStatusMessage.STATUS_PENDING, transaction=transaction_obj)

    result = simulate_payment(
        payment_provider=payment_method,
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

    notification_results = consume_payment_messages(order_id=order.id)

    if transaction_obj.status == PaymentTransaction.STATUS_SUCCESS:
        cart.items.all().delete()
    order.refresh_from_db()
    recipient = _notification_recipient(order)
    notification = notification_results.get(
        order.id,
        {
            "channel": "email",
            "recipient": recipient,
            "status": "queued",
            "detail": "Notification processing pending.",
        },
    )
    return order, transaction_obj, notification
