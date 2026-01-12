from django.test import TestCase, override_settings
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken
import pyotp

from users.models import AccessTokenBlocklist, User


class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_and_login(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "test@example.com", "password": "StrongPass123!", "full_name": "Test User", "recaptcha_token": "ok"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        login = self.client.post(
            "/api/auth/login/",
            {"email": "test@example.com", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("access", login.data)
        token = AccessToken(login.data["access"])
        self.assertGreater(token["exp"], token["iat"])

    def test_2fa_login(self):
        user = User.objects.create_user(email="twofa@example.com", password="StrongPass123!")
        user.otp_secret = pyotp.random_base32()
        user.is_2fa_enabled = True
        user.save()

        totp = pyotp.TOTP(user.otp_secret)
        response = self.client.post(
            "/api/auth/login/",
            {"email": "twofa@example.com", "password": "StrongPass123!", "code": totp.now()},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_refresh_rotation(self):
        user = User.objects.create_user(email="refresh@example.com", password="StrongPass123!")
        login = self.client.post(
            "/api/auth/login/",
            {"email": "refresh@example.com", "password": "StrongPass123!"},
            format="json",
        )
        refresh = login.data["refresh"]
        refresh_resp = self.client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(refresh_resp.status_code, 200)
        new_refresh = refresh_resp.data.get("refresh")
        self.assertNotEqual(refresh, new_refresh)

        reuse_resp = self.client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(reuse_resp.status_code, 401)

    def test_logout_blacklists_refresh(self):
        user = User.objects.create_user(email="logout@example.com", password="StrongPass123!")
        login = self.client.post(
            "/api/auth/login/",
            {"email": "logout@example.com", "password": "StrongPass123!"},
            format="json",
        )
        refresh = login.data["refresh"]
        logout = self.client.post(
            "/api/auth/logout/",
            {"refresh": refresh},
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}",
            format="json",
        )
        self.assertEqual(logout.status_code, 200)
        reuse = self.client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(reuse.status_code, 401)

    def test_password_validation(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "weak@example.com", "password": "123", "full_name": "Weak", "recaptcha_token": "ok"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    @override_settings(RECAPTCHA_SECRET_KEY="fake")
    def test_recaptcha_required(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "captcha@example.com", "password": "StrongPass123!", "full_name": "Cap", "recaptcha_token": ""},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_logout_all(self):
        user = User.objects.create_user(email="all@example.com", password="StrongPass123!")
        login = self.client.post(
            "/api/auth/login/",
            {"email": "all@example.com", "password": "StrongPass123!"},
            format="json",
        )
        response = self.client.post(
            "/api/auth/logout-all/",
            {},
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}",
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_logout_all_requires_auth(self):
        response = self.client.post(
            "/api/auth/logout-all/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_login_requires_2fa_code(self):
        user = User.objects.create_user(email="need2fa@example.com", password="StrongPass123!")
        user.otp_secret = pyotp.random_base32()
        user.is_2fa_enabled = True
        user.save()
        response = self.client.post(
            "/api/auth/login/",
            {"email": "need2fa@example.com", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_logout_missing_refresh(self):
        user = User.objects.create_user(email="logoutmissing@example.com", password="StrongPass123!")
        login = self.client.post(
            "/api/auth/login/",
            {"email": "logoutmissing@example.com", "password": "StrongPass123!"},
            format="json",
        )
        response = self.client.post(
            "/api/auth/logout/",
            {},
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}",
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_2fa_setup_requires_auth(self):
        response = self.client.post(
            "/api/auth/2fa/setup/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_register_invalid_email(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "not-an-email", "password": "StrongPass123!", "full_name": "Bad", "recaptcha_token": "ok"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_register_missing_fields(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "", "password": "", "full_name": "", "recaptcha_token": "ok"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_register_duplicate_email(self):
        User.objects.create_user(email="dup@example.com", password="StrongPass123!")
        response = self.client.post(
            "/api/auth/register/",
            {"email": "dup@example.com", "password": "StrongPass123!", "full_name": "Dup", "recaptcha_token": "ok"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_login_invalid_password(self):
        User.objects.create_user(email="badpass@example.com", password="StrongPass123!")
        response = self.client.post(
            "/api/auth/login/",
            {"email": "badpass@example.com", "password": "WrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_refresh_invalid_token(self):
        response = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": "invalid.token.here"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_refresh_missing_token(self):
        response = self.client.post(
            "/api/auth/token/refresh/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_access_token_revocation(self):
        user = User.objects.create_user(email="revoke@example.com", password="StrongPass123!")
        login = self.client.post(
            "/api/auth/login/",
            {"email": "revoke@example.com", "password": "StrongPass123!"},
            format="json",
        )
        access = login.data["access"]
        revoke = self.client.post(
            "/api/auth/token/revoke/",
            {},
            HTTP_AUTHORIZATION=f"Bearer {access}",
            format="json",
        )
        self.assertEqual(revoke.status_code, 200)
        blocked = self.client.post(
            "/api/auth/2fa/setup/",
            {},
            HTTP_AUTHORIZATION=f"Bearer {access}",
            format="json",
        )
        self.assertEqual(blocked.status_code, 401)

    def test_revoke_requires_access_token(self):
        user = User.objects.create_user(email="revoke2@example.com", password="StrongPass123!")
        login = self.client.post(
            "/api/auth/login/",
            {"email": "revoke2@example.com", "password": "StrongPass123!"},
            format="json",
        )
        response = self.client.post(
            "/api/auth/token/revoke/",
            {},
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}bad",
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_login_unknown_email(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": "missing@example.com", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_cleanup_access_tokens(self):
        expired = AccessTokenBlocklist.objects.create(
            jti="expired",
            expires_at=timezone.now() - timedelta(days=1),
        )
        AccessTokenBlocklist.objects.create(
            jti="active",
            expires_at=timezone.now() + timedelta(days=1),
        )
        call_command("cleanup_access_tokens")
        self.assertFalse(AccessTokenBlocklist.objects.filter(jti=expired.jti).exists())

    def test_revoke_without_auth(self):
        response = self.client.post(
            "/api/auth/token/revoke/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 401)
