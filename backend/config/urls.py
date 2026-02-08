from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.views.decorators.cache import cache_control
from django.views.static import serve

from users.views import password_reset_confirm_page

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
    path("api/auth/reset/<uid>/<token>/", password_reset_confirm_page, name="password_reset_confirm"),
    path("api/auth/", include("users.urls")),
    path("api/catalog/", include("catalog.urls")),
    path("api/commerce/", include("commerce.urls")),
    path("api/auth/", include("dj_rest_auth.urls")),
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),
    path("api/auth/", include("django.contrib.auth.urls")),
]

if settings.DEBUG:
    media_view = cache_control(max_age=86400)(serve)
    urlpatterns += [
        path("media/<path:path>", media_view, {"document_root": settings.MEDIA_ROOT}),
    ]
