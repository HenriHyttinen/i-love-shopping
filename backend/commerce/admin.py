from django.contrib import admin

from .models import (
    Cart,
    CartItem,
    DeliveryOption,
    Order,
    OrderItem,
    OrderStatusEvent,
    PaymentStatusMessage,
    PaymentTransaction,
    RefundRequest,
)


admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(PaymentTransaction)
admin.site.register(PaymentStatusMessage)
admin.site.register(OrderStatusEvent)
admin.site.register(DeliveryOption)
admin.site.register(RefundRequest)
