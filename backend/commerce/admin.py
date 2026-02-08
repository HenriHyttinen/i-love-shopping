from django.contrib import admin

from .models import Cart, CartItem, Order, OrderItem, OrderStatusEvent, PaymentStatusMessage, PaymentTransaction


admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(PaymentTransaction)
admin.site.register(PaymentStatusMessage)
admin.site.register(OrderStatusEvent)
