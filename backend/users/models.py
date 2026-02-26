from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from .fields import EncryptedTextField
from .security import hash_token_identifier


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CUSTOMER = "customer"
    ROLE_ADMIN = "admin"
    ROLE_SUPPORT = "support"
    ROLE_SALES = "sales"

    ROLE_CHOICES = [
        (ROLE_CUSTOMER, "Customer"),
        (ROLE_ADMIN, "Admin"),
        (ROLE_SUPPORT, "Support"),
        (ROLE_SALES, "Sales"),
    ]

    email = models.EmailField(unique=True)
    full_name = EncryptedTextField(blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    otp_secret = EncryptedTextField(blank=True)
    is_2fa_enabled = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class AccessTokenBlocklist(models.Model):
    jti = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.jti and len(self.jti) != 64:
            self.jti = hash_token_identifier(self.jti)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.jti
