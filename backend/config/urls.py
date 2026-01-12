from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.views.decorators.cache import cache_control
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
    path("api/auth/", include("users.urls")),
    path("api/catalog/", include("catalog.urls")),
    path("api/auth/", include("dj_rest_auth.urls")),
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),
]

if settings.DEBUG:
    media_view = cache_control(max_age=86400)(serve)
    urlpatterns += [
        path("media/<path:path>", media_view, {"document_root": settings.MEDIA_ROOT}),
    ]
