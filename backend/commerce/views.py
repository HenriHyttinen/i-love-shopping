from django.db import models, transaction
from django.db.models import Prefetch
from django.utils.dateparse import parse_date
from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Product

from .models import CartItem, Order, OrderStatusEvent, PaymentStatusMessage, PaymentTransaction
from .serializers import (
    CartItemMutationSerializer,
    CartItemUpdateSerializer,
    CheckoutSerializer,
    OrderSerializer,
)
from .services import (
    cart_totals,
    consume_payment_messages,
    get_or_create_cart,
    is_allowed_payment_order_transition,
    map_message_status_to_order_status,
    place_order_from_cart,
    publish_payment_message,
    recommended_products,
)


class CartView(APIView):
    permission_classes = [permissions.AllowAny]

    def _resolve_cart(self, request):
        guest_token = request.headers.get("X-Guest-Cart-Token", "").strip()
        if request.user and request.user.is_authenticated:
            cart = get_or_create_cart(user=request.user)
            return cart, ""
        cart = get_or_create_cart(guest_token=guest_token)
        return cart, cart.guest_token

    def get(self, request):
        cart, guest_token = self._resolve_cart(request)
        payload = cart_totals(cart)
        payload["recommended_products"] = recommended_products(cart)
        payload["guest_cart_token"] = guest_token
        return Response(payload)


class CartItemsView(APIView):
    permission_classes = [permissions.AllowAny]

    def _resolve_cart(self, request):
        guest_token = request.headers.get("X-Guest-Cart-Token", "").strip()
        if request.user and request.user.is_authenticated:
            return get_or_create_cart(user=request.user), ""
        cart = get_or_create_cart(guest_token=guest_token)
        return cart, cart.guest_token

    @transaction.atomic
    def post(self, request):
        serializer = CartItemMutationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = Product.objects.select_for_update().filter(id=serializer.validated_data["product_id"]).first()
        if not product or not product.is_active:
            return Response({"detail": "Product not found."}, status=404)
        if product.stock_quantity < serializer.validated_data["quantity"]:
            return Response({"detail": "Requested quantity is out of stock."}, status=400)

        cart, guest_token = self._resolve_cart(request)
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": serializer.validated_data["quantity"], "unit_price": product.price},
        )
        if not created:
            new_quantity = item.quantity + serializer.validated_data["quantity"]
            if new_quantity > product.stock_quantity:
                return Response({"detail": "Requested quantity is out of stock."}, status=400)
            item.quantity = new_quantity
            item.unit_price = product.price
            item.save(update_fields=["quantity", "unit_price", "updated_at"])

        payload = cart_totals(cart)
        payload["recommended_products"] = recommended_products(cart)
        payload["guest_cart_token"] = guest_token
        return Response(payload, status=201)


class CartItemDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def _resolve_cart(self, request):
        guest_token = request.headers.get("X-Guest-Cart-Token", "").strip()
        if request.user and request.user.is_authenticated:
            return get_or_create_cart(user=request.user), ""
        cart = get_or_create_cart(guest_token=guest_token)
        return cart, cart.guest_token

    @transaction.atomic
    def patch(self, request, item_id):
        serializer = CartItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart, guest_token = self._resolve_cart(request)
        item = cart.items.select_related("product").filter(id=item_id).first()
        if not item:
            return Response({"detail": "Cart item not found."}, status=404)

        quantity = serializer.validated_data["quantity"]
        if quantity == 0:
            item.delete()
        else:
            if quantity > item.product.stock_quantity:
                return Response({"detail": "Requested quantity is out of stock."}, status=400)
            item.quantity = quantity
            item.save(update_fields=["quantity", "updated_at"])

        payload = cart_totals(cart)
        payload["recommended_products"] = recommended_products(cart)
        payload["guest_cart_token"] = guest_token
        return Response(payload)

    @transaction.atomic
    def delete(self, request, item_id):
        cart, guest_token = self._resolve_cart(request)
        item = cart.items.filter(id=item_id).first()
        if not item:
            return Response({"detail": "Cart item not found."}, status=404)
        item.delete()
        payload = cart_totals(cart)
        payload["recommended_products"] = recommended_products(cart)
        payload["guest_cart_token"] = guest_token
        return Response(payload)


class CheckoutPrefillView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if request.user and request.user.is_authenticated:
            return Response(
                {
                    "full_name": request.user.full_name,
                    "email": request.user.email,
                }
            )
        return Response({"full_name": "", "email": ""})


class CheckoutSummaryView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        guest_token = request.headers.get("X-Guest-Cart-Token", "").strip()
        cart = get_or_create_cart(user=request.user if request.user.is_authenticated else None, guest_token=guest_token)
        payload = cart_totals(cart)
        payload["shipping_options"] = [
            {"code": "standard", "label": "Standard", "cost": "7.90"},
            {"code": "express", "label": "Express", "cost": "18.90"},
        ]
        payload["guest_cart_token"] = cart.guest_token if not request.user.is_authenticated else ""
        return Response(payload)


class CheckoutPlaceOrderView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        guest_token = request.headers.get("X-Guest-Cart-Token", "").strip()
        cart = get_or_create_cart(user=request.user if request.user.is_authenticated else None, guest_token=guest_token)

        try:
            order, payment_txn, notification = place_order_from_cart(
                cart=cart,
                customer_payload={
                    "full_name": serializer.validated_data["full_name"],
                    "email": serializer.validated_data["email"],
                    "phone": serializer.validated_data["phone"],
                    "shipping_address": serializer.validated_data["shipping_address"],
                },
                payment_payload={
                    "payment_token": serializer.validated_data.get("payment_token", ""),
                },
                shipping_option=serializer.validated_data["shipping_option"],
                payment_method=serializer.validated_data["payment_method"],
                user=request.user if request.user.is_authenticated else None,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        except Exception:
            return Response(
                {"detail": "Network error while processing payment. Please retry."},
                status=502,
            )

        return Response(
            {
                "order": OrderSerializer(order).data,
                "payment": {
                    "status": payment_txn.status,
                    "failure_code": payment_txn.failure_code,
                    "external_reference": payment_txn.external_reference,
                },
                "notification": notification,
            },
            status=status.HTTP_201_CREATED,
        )


class OrderListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = Order.objects.filter(user=request.user).prefetch_related(
            "status_events",
            Prefetch("items"),
        )
        status_filter = request.query_params.get("status", "").strip()
        date_from = request.query_params.get("date_from", "").strip()
        date_to = request.query_params.get("date_to", "").strip()

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if date_from:
            parsed = parse_date(date_from)
            if not parsed:
                return Response({"detail": "Invalid date_from format. Use YYYY-MM-DD."}, status=400)
            queryset = queryset.filter(created_at__date__gte=parsed)

        if date_to:
            parsed = parse_date(date_to)
            if not parsed:
                return Response({"detail": "Invalid date_to format. Use YYYY-MM-DD."}, status=400)
            queryset = queryset.filter(created_at__date__lte=parsed)

        return Response(OrderSerializer(queryset, many=True).data)


class PaymentConfigView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY or ""})


class PaymentCallbackSimulationView(APIView):
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request):
        configured_secret = (settings.PAYMENT_CALLBACK_SECRET or "").strip()
        if configured_secret:
            provided_secret = request.headers.get("X-Payment-Callback-Secret", "").strip()
            if provided_secret != configured_secret:
                return Response({"detail": "Unauthorized callback."}, status=403)

        external_reference = str(request.data.get("external_reference", "")).strip()
        callback_status = str(request.data.get("status", "")).strip().lower()
        failure_code = str(request.data.get("failure_code", "")).strip()
        message = str(request.data.get("message", "")).strip()

        if not external_reference:
            return Response({"detail": "external_reference is required."}, status=400)
        if callback_status not in {"pending", "success", "failure"}:
            return Response({"detail": "status must be one of: pending, success, failure."}, status=400)

        transaction_obj = (
            PaymentTransaction.objects.select_for_update().select_related("order").filter(external_reference=external_reference).first()
        )
        if not transaction_obj:
            return Response({"detail": "Payment transaction not found."}, status=404)

        target_order_status = map_message_status_to_order_status(callback_status)
        if not is_allowed_payment_order_transition(transaction_obj.order.status, target_order_status):
            return Response(
                {"detail": f"Invalid payment status transition to {target_order_status}."},
                status=409,
            )

        transaction_obj.status = callback_status
        transaction_obj.failure_code = failure_code if callback_status == "failure" else ""
        transaction_obj.save(update_fields=["status", "failure_code", "updated_at"])

        publish_payment_message(
            order=transaction_obj.order,
            status=callback_status,
            transaction=transaction_obj,
            payload={"failure_code": failure_code, "message": message},
        )
        consume_payment_messages(order_id=transaction_obj.order_id)

        return Response(
            {
                "detail": "Callback processed.",
                "order_id": transaction_obj.order_id,
                "transaction_id": transaction_obj.id,
                "status": callback_status,
                "published": PaymentStatusMessage.objects.filter(
                    transaction=transaction_obj,
                    status=callback_status,
                ).count(),
            }
        )


class OrderDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_id):
        order = (
            Order.objects.filter(user=request.user, id=order_id)
            .prefetch_related("status_events", "items")
            .first()
        )
        if not order:
            return Response({"detail": "Order not found."}, status=404)
        serialized = OrderSerializer(order).data
        serialized["items"] = [
            {
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
            }
            for item in order.items.all()
        ]
        return Response(serialized)


class OrderCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, order_id):
        order = (
            Order.objects.select_for_update()
            .filter(user=request.user, id=order_id)
            .prefetch_related("items")
            .first()
        )
        if not order:
            return Response({"detail": "Order not found."}, status=404)
        if order.is_processed:
            return Response({"detail": "Order already processed and cannot be cancelled."}, status=400)
        if order.status == Order.STATUS_CANCELLED:
            return Response({"detail": "Order already cancelled."}, status=400)
        if order.status not in {Order.STATUS_PENDING_PAYMENT, Order.STATUS_PAYMENT_SUCCESSFUL}:
            return Response({"detail": "Order cannot be cancelled in its current state."}, status=400)

        order.status = Order.STATUS_CANCELLED
        order.save(update_fields=["status", "updated_at"])

        for item in order.items.all():
            Product.objects.filter(id=item.product_id).update(stock_quantity=models.F("stock_quantity") + item.quantity)

        OrderStatusEvent.objects.create(order=order, status=Order.STATUS_CANCELLED, note="Order cancelled by user")
        return Response({"detail": "Order cancelled."})


class OrderProcessView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, order_id):
        if not request.user.is_staff:
            return Response({"detail": "Only staff can process orders."}, status=403)

        order = Order.objects.select_for_update().filter(id=order_id).first()
        if not order:
            return Response({"detail": "Order not found."}, status=404)
        if order.status != Order.STATUS_PAYMENT_SUCCESSFUL:
            return Response({"detail": "Only paid orders can be marked as processed."}, status=400)
        if order.is_processed:
            return Response({"detail": "Order already processed."}, status=200)

        order.is_processed = True
        order.save(update_fields=["is_processed", "updated_at"])
        OrderStatusEvent.objects.create(order=order, status=order.status, note="Order marked as processed")
        return Response({"detail": "Order marked as processed."})
