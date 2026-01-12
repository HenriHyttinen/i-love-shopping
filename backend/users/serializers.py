from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
import pyotp
from allauth.account.models import EmailAddress

from .utils import verify_recaptcha

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    recaptcha_token = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("email", "password", "full_name", "recaptcha_token")

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_recaptcha_token(self, value):
        if not verify_recaptcha(value):
            raise serializers.ValidationError("CAPTCHA verification failed")
        return value

    def create(self, validated_data):
        validated_data.pop("recaptcha_token", None)
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        EmailAddress.objects.get_or_create(
            user=user,
            email=user.email,
            defaults={"verified": True, "primary": True},
        )
        return user


class TwoFASetupSerializer(serializers.Serializer):
    otp_secret = serializers.CharField(read_only=True)
    otpauth_url = serializers.CharField(read_only=True)


class TwoFAVerifySerializer(serializers.Serializer):
    code = serializers.CharField()

    def validate_code(self, value):
        if not value.isdigit() or len(value) not in (6, 8):
            raise serializers.ValidationError("Invalid code format")
        return value


class TwoFADisableSerializer(serializers.Serializer):
    code = serializers.CharField()


class LoginTwoFARequiredSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    code = serializers.CharField(required=False, write_only=True)

    def validate(self, attrs):
        user = User.objects.filter(email=attrs["email"]).first()
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        if not user.check_password(attrs["password"]):
            raise serializers.ValidationError("Invalid credentials")
        if user.is_2fa_enabled:
            code = attrs.get("code")
            if not code:
                raise serializers.ValidationError("Two-factor code required")
            totp = pyotp.TOTP(user.otp_secret)
            if not totp.verify(code):
                raise serializers.ValidationError("Invalid two-factor code")
        attrs["user"] = user
        return attrs
