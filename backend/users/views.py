import base64
from datetime import datetime, timezone
from io import BytesIO

import pyotp
import qrcode
import requests
from django.shortcuts import render
from django.contrib.auth import get_user_model
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

from .serializers import (
    LoginTwoFARequiredSerializer,
    RegisterSerializer,
    TwoFADisableSerializer,
    TwoFASetupSerializer,
    TwoFAVerifySerializer,
)
from .models import AccessTokenBlocklist
from allauth.account.models import EmailAddress


def password_reset_confirm_page(request, uid, token):
    return render(request, "password_reset_confirm.html", {"uid": uid, "token": token})

def _get_user_from_google_token(access_token):
    resp = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=5,
    )
    if resp.status_code != 200:
        return None, Response({"detail": "Invalid Google token"}, status=400)
    data = resp.json()
    email = data.get("email")
    if not email:
        return None, Response({"detail": "Email not found from Google"}, status=400)

    user_model = get_user_model()
    user = user_model.objects.filter(email__iexact=email).first()
    if not user:
        user = user_model.objects.create_user(
            email=email,
            password=None,
            full_name=data.get("name", ""),
        )
    EmailAddress.objects.get_or_create(
        user=user,
        email=user.email,
        defaults={"verified": True, "primary": True},
    )
    return user, None


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": {"id": user.id, "email": user.email, "full_name": user.full_name},
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginTwoFARequiredSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return Response({"refresh": str(refresh), "access": str(refresh.access_token)})


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token required"}, status=400)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({"detail": "Invalid token"}, status=400)
        return Response({"detail": "Logged out"})


class LogoutAllView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        RefreshToken.for_user(request.user).blacklist()
        return Response({"detail": "Logged out from all sessions"})


class RevokeAccessTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        raw_token = request.auth
        if not raw_token:
            return Response({"detail": "Access token required"}, status=400)
        try:
            token = AccessToken(str(raw_token))
        except Exception:
            return Response({"detail": "Invalid access token"}, status=400)
        jti = token.get("jti")
        exp = token.get("exp")
        if not jti or not exp:
            return Response({"detail": "Invalid token payload"}, status=400)
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        AccessTokenBlocklist.objects.get_or_create(jti=jti, defaults={"expires_at": expires_at})
        return Response({"detail": "Access token revoked"})


class TwoFASetupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.otp_secret:
            user.otp_secret = pyotp.random_base32()
            user.save(update_fields=["otp_secret"])
        totp = pyotp.TOTP(user.otp_secret)
        otpauth_url = totp.provisioning_uri(name=user.email, issuer_name="I Love Shopping")

        qr = qrcode.make(otpauth_url)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        qr_b64 = base64.b64encode(buffer.getvalue()).decode("ascii")

        serializer = TwoFASetupSerializer(
            {"otp_secret": user.otp_secret, "otpauth_url": otpauth_url}
        )
        return Response({**serializer.data, "qr_code_base64": qr_b64})


class TwoFAVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TwoFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        totp = pyotp.TOTP(user.otp_secret)
        if not totp.verify(serializer.validated_data["code"]):
            return Response({"detail": "Invalid code"}, status=400)
        user.is_2fa_enabled = True
        user.save(update_fields=["is_2fa_enabled"])
        return Response({"detail": "2FA enabled"})


class TwoFADisableView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TwoFADisableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        totp = pyotp.TOTP(user.otp_secret)
        if not totp.verify(serializer.validated_data["code"]):
            return Response({"detail": "Invalid code"}, status=400)
        user.is_2fa_enabled = False
        user.save(update_fields=["is_2fa_enabled"])
        return Response({"detail": "2FA disabled"})


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter


class GoogleTokenLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        access_token = request.data.get("access_token")
        if not access_token:
            return Response({"detail": "access_token required"}, status=400)
        user, error = _get_user_from_google_token(access_token)
        if error:
            return error
        refresh = RefreshToken.for_user(user)
        return Response({"refresh": str(refresh), "access": str(refresh.access_token)})


class GoogleCodeLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        code = request.data.get("code")
        redirect_uri = request.data.get("redirect_uri")
        if not code:
            return Response({"detail": "code required"}, status=400)
        if not redirect_uri:
            return Response({"detail": "redirect_uri required"}, status=400)

        from django.conf import settings

        if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
            return Response({"detail": "Google OAuth not configured"}, status=400)

        token_resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=5,
        )
        if token_resp.status_code != 200:
            return Response({"detail": "Invalid Google code"}, status=400)

        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return Response({"detail": "Google access token missing"}, status=400)

        user, error = _get_user_from_google_token(access_token)
        if error:
            return error
        refresh = RefreshToken.for_user(user)
        return Response({"refresh": str(refresh), "access": str(refresh.access_token)})


class GoogleClientIdView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.conf import settings

        return Response({"client_id": settings.GOOGLE_OAUTH_CLIENT_ID or ""})


class RecaptchaSiteKeyView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.conf import settings

        return Response({"site_key": settings.RECAPTCHA_SITE_KEY or ""})
