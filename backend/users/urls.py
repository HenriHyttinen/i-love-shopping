from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    GoogleLogin,
    GoogleClientIdView,
    GoogleTokenLoginView,
    RecaptchaSiteKeyView,
    LoginView,
    LogoutView,
    LogoutAllView,
    RevokeAccessTokenView,
    RegisterView,
    TwoFADisableView,
    TwoFASetupView,
    TwoFAVerifyView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("logout-all/", LogoutAllView.as_view(), name="logout_all"),
    path("token/revoke/", RevokeAccessTokenView.as_view(), name="revoke_access"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("2fa/setup/", TwoFASetupView.as_view(), name="2fa_setup"),
    path("2fa/verify/", TwoFAVerifyView.as_view(), name="2fa_verify"),
    path("2fa/disable/", TwoFADisableView.as_view(), name="2fa_disable"),
    path("oauth/google/", GoogleTokenLoginView.as_view(), name="google_login"),
    path("oauth/google-allauth/", GoogleLogin.as_view(), name="google_login_allauth"),
    path("oauth/google-client-id/", GoogleClientIdView.as_view(), name="google_client_id"),
    path("recaptcha-site-key/", RecaptchaSiteKeyView.as_view(), name="recaptcha_site_key"),
]
