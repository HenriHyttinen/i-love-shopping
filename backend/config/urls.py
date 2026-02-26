from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.views.decorators.cache import cache_control
from django.views.static import serve

from config.views import ContactSupportView, custom_404
from users.views import password_reset_confirm_page

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
    path("products/", TemplateView.as_view(template_name="product_list.html"), name="product_list_page"),
    path("login/", TemplateView.as_view(template_name="login.html"), name="login_page"),
    path("register/", TemplateView.as_view(template_name="register.html"), name="register_page"),
    path("account/", TemplateView.as_view(template_name="account.html"), name="account_page"),
    path("cart/", TemplateView.as_view(template_name="cart.html"), name="cart_page"),
    path("checkout/", TemplateView.as_view(template_name="checkout.html"), name="checkout_page"),
    path("orders/", TemplateView.as_view(template_name="orders.html"), name="orders_page"),
    path("search/", TemplateView.as_view(template_name="search.html"), name="search_page"),
    path("order-confirmation/", TemplateView.as_view(template_name="order_confirmation.html"), name="order_confirmation_page"),
    path("contact/", TemplateView.as_view(template_name="contact.html"), name="contact_page"),
    path("about/", TemplateView.as_view(template_name="about.html"), name="about_page"),
    path("admin-panel/", TemplateView.as_view(template_name="admin_panel.html"), name="admin_panel_page"),
    path("products/<int:product_id>/", TemplateView.as_view(template_name="product_detail.html"), name="product_detail_page"),
    path("api/auth/reset/<uid>/<token>/", password_reset_confirm_page, name="password_reset_confirm"),
    path("api/auth/", include("users.urls")),
    path("api/catalog/", include("catalog.urls")),
    path("api/commerce/", include("commerce.urls")),
    path("api/support/contact/", ContactSupportView.as_view(), name="support_contact"),
    path("api/auth/", include("dj_rest_auth.urls")),
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),
    path("api/auth/", include("django.contrib.auth.urls")),
]

if settings.DEBUG:
    media_view = cache_control(max_age=86400)(serve)
    urlpatterns += [
        path("media/<path:path>", media_view, {"document_root": settings.MEDIA_ROOT}),
    ]

handler404 = custom_404
