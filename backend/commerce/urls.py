from django.urls import path

from .views import (
    CartItemDetailView,
    CartItemsView,
    CartView,
    CheckoutPlaceOrderView,
    CheckoutPrefillView,
    CheckoutSummaryView,
    OrderCancelView,
    OrderDetailView,
    OrderListView,
)

urlpatterns = [
    path("cart/", CartView.as_view(), name="commerce_cart"),
    path("cart/items/", CartItemsView.as_view(), name="commerce_cart_items"),
    path("cart/items/<int:item_id>/", CartItemDetailView.as_view(), name="commerce_cart_item_detail"),
    path("checkout/prefill/", CheckoutPrefillView.as_view(), name="commerce_checkout_prefill"),
    path("checkout/summary/", CheckoutSummaryView.as_view(), name="commerce_checkout_summary"),
    path("checkout/place-order/", CheckoutPlaceOrderView.as_view(), name="commerce_checkout_place_order"),
    path("orders/", OrderListView.as_view(), name="commerce_order_list"),
    path("orders/<int:order_id>/", OrderDetailView.as_view(), name="commerce_order_detail"),
    path("orders/<int:order_id>/cancel/", OrderCancelView.as_view(), name="commerce_order_cancel"),
]
