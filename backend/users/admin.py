from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import AccessTokenBlocklist, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    list_display = ("email", "full_name", "is_staff", "is_2fa_enabled")
    list_filter = ("is_staff", "is_superuser", "is_active")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("full_name",)}),
        (
            "Security",
            {"fields": ("is_2fa_enabled", "otp_secret")},
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
    search_fields = ("email",)


@admin.register(AccessTokenBlocklist)
class AccessTokenBlocklistAdmin(admin.ModelAdmin):
    list_display = ("jti", "expires_at", "created_at")
    search_fields = ("jti",)
