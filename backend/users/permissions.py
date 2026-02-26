from rest_framework import permissions


class IsAdminWith2FA(permissions.BasePermission):
    message = "Admin access requires enabled 2FA."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if not user.is_staff:
            return False
        return bool(user.is_2fa_enabled)

